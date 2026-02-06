"""
Webhook handlers for external service events.

Endpoints:
- POST /livekit: LiveKit room/participant events
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from livekit import api

from app.core.config import get_settings
from app.core.database import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# LiveKit Webhook Handler
# =============================================================================


@router.post("/livekit")
async def livekit_webhook(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """
    Handle LiveKit webhook events.

    Events handled:
    - participant_joined: Update participant connection status
    - participant_left: Update participant disconnection status
    - track_published: Log audio track publication (for verification)
    - room_finished: Log room cleanup confirmation

    Security: Validates webhook signature using LiveKit API key/secret.
    """
    settings = get_settings()

    # Get raw body for signature verification
    body = await request.body()

    # Skip signature validation in dev mode
    if not settings.livekit_api_key or settings.livekit_api_key == "your-livekit-api-key":
        logger.warning("LiveKit webhook received in dev mode - signature not validated")
        try:
            event_data = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
    else:
        # Validate webhook signature
        try:
            receiver = api.WebhookReceiver(
                settings.livekit_api_key,
                settings.livekit_api_secret,
            )
            event = receiver.receive(body.decode(), authorization or "")
            event_data = _event_to_dict(event)
        except Exception as e:
            logger.error(f"Webhook signature validation failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Route event to handler
    event_type = event_data.get("event")
    logger.info(f"Received LiveKit event: {event_type}")

    if event_type == "participant_joined":
        await _handle_participant_joined(event_data)
    elif event_type == "participant_left":
        await _handle_participant_left(event_data)
    elif event_type == "track_published":
        await _handle_track_published(event_data)
    elif event_type == "room_finished":
        await _handle_room_finished(event_data)
    else:
        logger.debug(f"Unhandled event type: {event_type}")

    return {"status": "ok"}


# =============================================================================
# Event Handlers
# =============================================================================


async def _handle_participant_joined(event_data: dict) -> None:
    """
    Handle participant_joined event.

    Updates the session_participants record with connection status.
    """
    room_name = event_data.get("room", {}).get("name")
    participant = event_data.get("participant", {})
    identity = participant.get("identity")  # This is the user_id

    if not room_name or not identity:
        logger.warning(f"Missing room or identity in participant_joined: {event_data}")
        return

    logger.info(f"Participant {identity} joined room {room_name}")

    # Find session by room name
    supabase = get_supabase()
    session_result = (
        supabase.table("sessions")
        .select("id")
        .eq("livekit_room_name", room_name)
        .execute()
    )

    if not session_result.data:
        logger.warning(f"Session not found for room {room_name}")
        return

    session_id = session_result.data[0]["id"]

    # Update participant connection status
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("session_participants").update({
        "connected_at": now,
        "is_connected": True,
    }).eq("session_id", session_id).eq("user_id", identity).execute()

    logger.info(f"Updated connection status for {identity} in session {session_id}")


async def _handle_participant_left(event_data: dict) -> None:
    """
    Handle participant_left event.

    Updates the session_participants record with disconnection status.
    """
    room_name = event_data.get("room", {}).get("name")
    participant = event_data.get("participant", {})
    identity = participant.get("identity")

    if not room_name or not identity:
        logger.warning(f"Missing room or identity in participant_left: {event_data}")
        return

    logger.info(f"Participant {identity} left room {room_name}")

    # Find session by room name
    supabase = get_supabase()
    session_result = (
        supabase.table("sessions")
        .select("id")
        .eq("livekit_room_name", room_name)
        .execute()
    )

    if not session_result.data:
        logger.warning(f"Session not found for room {room_name}")
        return

    session_id = session_result.data[0]["id"]

    # Update participant disconnection status
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("session_participants").update({
        "disconnected_at": now,
        "is_connected": False,
    }).eq("session_id", session_id).eq("user_id", identity).execute()

    logger.info(f"Updated disconnection status for {identity} in session {session_id}")


async def _handle_track_published(event_data: dict) -> None:
    """
    Handle track_published event.

    Logs when a participant publishes an audio track.
    Useful for verifying Forced Audio mode compliance.
    """
    room_name = event_data.get("room", {}).get("name")
    participant = event_data.get("participant", {})
    track = event_data.get("track", {})

    identity = participant.get("identity")
    track_type = track.get("type")
    track_source = track.get("source")

    logger.info(
        f"Track published in {room_name}: "
        f"participant={identity}, type={track_type}, source={track_source}"
    )


async def _handle_room_finished(event_data: dict) -> None:
    """
    Handle room_finished event.

    Logs when a room is closed by LiveKit (all participants left or timeout).
    """
    room = event_data.get("room", {})
    room_name = room.get("name")
    room_sid = room.get("sid")

    logger.info(f"Room finished: name={room_name}, sid={room_sid}")


# =============================================================================
# Helpers
# =============================================================================


def _event_to_dict(event: api.WebhookEvent) -> dict:
    """Convert LiveKit WebhookEvent to dict for processing."""
    return {
        "event": event.event,
        "room": {
            "name": event.room.name if event.room else None,
            "sid": event.room.sid if event.room else None,
        } if event.room else {},
        "participant": {
            "identity": event.participant.identity if event.participant else None,
            "sid": event.participant.sid if event.participant else None,
            "name": event.participant.name if event.participant else None,
        } if event.participant else {},
        "track": {
            "type": event.track.type if event.track else None,
            "source": event.track.source if event.track else None,
            "sid": event.track.sid if event.track else None,
        } if event.track else {},
    }
