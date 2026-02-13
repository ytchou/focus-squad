"""
Webhook handlers for external service events.

Endpoints:
- POST /livekit: LiveKit room/participant events
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Header, HTTPException, Request

if TYPE_CHECKING:
    from supabase import Client
from livekit import api

from app.core.config import get_settings
from app.core.constants import MIN_ACTIVE_MINUTES_FOR_COMPLETION
from app.core.database import get_supabase
from app.services.streak_service import StreakService

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# Pending Ratings Helper
# =============================================================================


def _create_pending_ratings(supabase: "Client", session_id: str, participants: list[dict]) -> int:
    """
    Create pending_ratings records for all human participants.

    Each participant gets a record listing the other human participants
    they need to rate. Only creates records if there are 2+ human participants.

    Args:
        supabase: Supabase client
        session_id: The completed session ID
        participants: List of session_participants records

    Returns:
        Number of pending_ratings records created
    """
    # Extract user_ids of human participants
    human_user_ids = [
        p.get("user_id")
        for p in participants
        if p.get("user_id") and p.get("participant_type") == "human"
    ]

    # Need at least 2 humans for peer rating
    if len(human_user_ids) < 2:
        logger.info(f"Session {session_id}: <2 humans, skipping pending_ratings")
        return 0

    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)
    created_count = 0

    for user_id in human_user_ids:
        # Get other human participants this user can rate
        rateable_ids = [uid for uid in human_user_ids if uid != user_id]

        try:
            supabase.table("pending_ratings").insert(
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "rateable_user_ids": rateable_ids,
                    "expires_at": expires_at.isoformat(),
                }
            ).execute()
            created_count += 1
        except Exception as e:
            logger.error(f"Failed to create pending_rating for user {user_id}: {e}")

    logger.info(
        f"Created {created_count} pending_ratings for session {session_id} "
        f"({len(human_user_ids)} human participants)"
    )
    return created_count


# =============================================================================
# Session Completion Helper
# =============================================================================


def is_session_completed(participant: dict, session_start_time: datetime) -> bool:
    """
    Check if a participant completed the session.

    Completed = present through both work blocks + meaningful engagement.
    Since phase lock guarantees joining during setup only:
    1. left_at IS NULL OR left_at >= start_time + 50 min (present at work_2 end)
    2. total_active_minutes >= 20 (meaningfully engaged)

    Args:
        participant: session_participants record dict
        session_start_time: Session start time (datetime with timezone)

    Returns:
        True if participant completed the session
    """
    # Must have meaningful engagement
    total_active = participant.get("total_active_minutes", 0) or 0
    if total_active < MIN_ACTIVE_MINUTES_FOR_COMPLETION:
        return False

    # Must be present through both work blocks (through minute 50)
    left_at_str = participant.get("left_at")
    if left_at_str is None:
        return True  # Still present = completed

    # Parse left_at
    if isinstance(left_at_str, str):
        if left_at_str.endswith("Z"):
            left_at_str = left_at_str[:-1] + "+00:00"
        left_at = datetime.fromisoformat(left_at_str)
    else:
        left_at = left_at_str

    # Must have stayed at least through minute 50 (end of work_2)
    work_2_end = session_start_time + timedelta(minutes=50)
    return left_at >= work_2_end


def _parse_session_start_time(start_time_str: str) -> datetime:
    """Parse session start time string to datetime."""
    if isinstance(start_time_str, datetime):
        return start_time_str
    if start_time_str.endswith("Z"):
        start_time_str = start_time_str[:-1] + "+00:00"
    return datetime.fromisoformat(start_time_str)


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
    - participant_left: Update participant disconnection status + active minutes
    - track_published: Log audio track publication (for verification)
    - room_finished: Mark session ended, award essence, schedule cleanup

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
        supabase.table("sessions").select("id").eq("livekit_room_name", room_name).execute()
    )

    if not session_result.data:
        logger.warning(f"Session not found for room {room_name}")
        return

    session_id = session_result.data[0]["id"]

    # Update participant connection status
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("session_participants").update(
        {
            "connected_at": now,
            "is_connected": True,
        }
    ).eq("session_id", session_id).eq("user_id", identity).execute()

    logger.info(f"Updated connection status for {identity} in session {session_id}")


async def _handle_participant_left(event_data: dict) -> None:
    """
    Handle participant_left event.

    Updates the session_participants record with:
    - disconnection timestamp
    - is_connected = false
    - total_active_minutes (accumulated across connect/disconnect cycles)
    - disconnect_count incremented
    """
    room_name = event_data.get("room", {}).get("name")
    participant = event_data.get("participant", {})
    identity = participant.get("identity")

    if not room_name or not identity:
        logger.warning(f"Missing room or identity in participant_left: {event_data}")
        return

    logger.info(f"Participant {identity} left room {room_name}")

    supabase = get_supabase()

    # Find session by room name
    session_result = (
        supabase.table("sessions").select("id").eq("livekit_room_name", room_name).execute()
    )

    if not session_result.data:
        logger.warning(f"Session not found for room {room_name}")
        return

    session_id = session_result.data[0]["id"]

    # Fetch participant's current state to calculate active minutes delta
    participant_result = (
        supabase.table("session_participants")
        .select("id, connected_at, total_active_minutes, disconnect_count")
        .eq("session_id", session_id)
        .eq("user_id", identity)
        .execute()
    )

    if not participant_result.data:
        logger.warning(f"Participant {identity} not found in session {session_id}")
        return

    p = participant_result.data[0]
    now = datetime.now(timezone.utc)

    # Calculate active minutes delta from this connection period
    active_minutes_delta = 0
    connected_at_str = p.get("connected_at")
    if connected_at_str:
        if isinstance(connected_at_str, str):
            if connected_at_str.endswith("Z"):
                connected_at_str = connected_at_str[:-1] + "+00:00"
            connected_at = datetime.fromisoformat(connected_at_str)
        else:
            connected_at = connected_at_str

        active_minutes_delta = int((now - connected_at).total_seconds() / 60)

    current_total = p.get("total_active_minutes") or 0
    current_disconnects = p.get("disconnect_count") or 0

    # Update participant record
    supabase.table("session_participants").update(
        {
            "disconnected_at": now.isoformat(),
            "is_connected": False,
            "total_active_minutes": current_total + active_minutes_delta,
            "disconnect_count": current_disconnects + 1,
        }
    ).eq("id", p["id"]).execute()

    logger.info(
        f"Updated disconnection for {identity} in session {session_id}: "
        f"+{active_minutes_delta} min active, disconnect #{current_disconnects + 1}"
    )

    # Check if all humans have disconnected (log only, LiveKit handles room cleanup)
    remaining = (
        supabase.table("session_participants")
        .select("id", count="exact")
        .eq("session_id", session_id)
        .eq("participant_type", "human")
        .eq("is_connected", True)
        .execute()
    )

    if remaining.count == 0:
        logger.info(
            f"All humans disconnected from session {session_id}. "
            "LiveKit will send room_finished when room times out."
        )


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

    When a room is closed by LiveKit (all participants left or timeout):
    1. Mark session as ended
    2. Award essence to qualifying participants
    3. Schedule cleanup task for stats + referrals
    """
    room = event_data.get("room", {})
    room_name = room.get("name")

    if not room_name:
        logger.warning(f"Missing room name in room_finished: {event_data}")
        return

    logger.info(f"Room finished: name={room_name}")

    supabase = get_supabase()

    # Find session
    session_result = (
        supabase.table("sessions")
        .select("id, start_time, current_phase")
        .eq("livekit_room_name", room_name)
        .execute()
    )

    if not session_result.data:
        logger.warning(f"Session not found for room {room_name}")
        return

    session = session_result.data[0]
    session_id = session["id"]

    # 1. Mark session as ended
    now = datetime.now(timezone.utc).isoformat()
    supabase.table("sessions").update(
        {
            "current_phase": "ended",
            "phase_started_at": now,
        }
    ).eq("id", session_id).execute()

    logger.info(f"Session {session_id} marked as ended")

    # 2. Award essence to qualifying participants
    session_start = _parse_session_start_time(session["start_time"])

    human_participants = (
        supabase.table("session_participants")
        .select("id, user_id, left_at, total_active_minutes, essence_earned")
        .eq("session_id", session_id)
        .eq("participant_type", "human")
        .execute()
    )

    essence_awarded = 0
    for p in human_participants.data or []:
        user_id = p.get("user_id")
        if not user_id:
            continue

        # Skip if already awarded
        if p.get("essence_earned"):
            continue

        # Check completion
        if not is_session_completed(p, session_start):
            logger.info(f"User {user_id} did not complete session {session_id}")
            continue

        # Award 1 Furniture Essence
        try:
            # Get current essence record
            essence_result = (
                supabase.table("furniture_essence")
                .select("balance, total_earned")
                .eq("user_id", user_id)
                .execute()
            )

            if essence_result.data:
                current = essence_result.data[0]
                supabase.table("furniture_essence").update(
                    {
                        "balance": current["balance"] + 1,
                        "total_earned": current["total_earned"] + 1,
                        "updated_at": now,
                    }
                ).eq("user_id", user_id).execute()
            else:
                supabase.table("furniture_essence").insert(
                    {"user_id": user_id, "balance": 1, "total_earned": 1}
                ).execute()

            # Log essence transaction
            supabase.table("essence_transactions").insert(
                {
                    "user_id": user_id,
                    "amount": 1,
                    "transaction_type": "session_complete",
                    "related_session_id": session_id,
                }
            ).execute()

            # Mark essence as earned for this participant
            supabase.table("session_participants").update({"essence_earned": True}).eq(
                "id", p["id"]
            ).execute()

            essence_awarded += 1
            logger.info(f"Awarded 1 essence to user {user_id} for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to award essence to user {user_id}: {e}")

        # Check weekly streak bonus
        try:
            streak_service = StreakService(supabase=supabase)
            streak_result = streak_service.increment_session_count(user_id)
            if streak_result:
                logger.info(
                    f"Streak bonus: +{streak_result.bonus_essence} essence "
                    f"to user {user_id} (threshold {streak_result.threshold_reached})"
                )
        except Exception as e:
            logger.error(f"Failed to process streak for user {user_id}: {e}")

    logger.info(f"Awarded essence to {essence_awarded} participants in session {session_id}")

    # 3. Create pending_ratings for peer review
    _create_pending_ratings(supabase, session_id, human_participants.data or [])

    # 4. Schedule cleanup task (handles stats + referrals)
    try:
        from app.tasks.livekit_tasks import cleanup_ended_session

        cleanup_ended_session.apply_async(
            args=[session_id],
            countdown=60,  # Delay 1 minute to let final DB writes settle
        )
        logger.info(f"Scheduled cleanup task for session {session_id}")
    except Exception as e:
        logger.warning(f"Failed to schedule cleanup task: {e}")


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
        }
        if event.room
        else {},
        "participant": {
            "identity": event.participant.identity if event.participant else None,
            "sid": event.participant.sid if event.participant else None,
            "name": event.participant.name if event.participant else None,
        }
        if event.participant
        else {},
        "track": {
            "type": event.track.type if event.track else None,
            "source": event.track.source if event.track else None,
            "sid": event.track.sid if event.track else None,
        }
        if event.track
        else {},
    }
