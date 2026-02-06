"""
Celery tasks for LiveKit room management.

Handles:
- Scheduled room creation (T-30s before session)
- Room cleanup after sessions end
"""

import asyncio
import logging
from typing import Optional

from app.core.celery_app import celery_app
from app.core.constants import ROOM_CLEANUP_DELAY_MINUTES
from app.core.database import get_supabase
from app.models.session import TableMode
from app.services.livekit_service import LiveKitService, LiveKitServiceError

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in Celery tasks."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(LiveKitServiceError,),
)
def create_livekit_room(self, session_id: str) -> dict:
    """
    Create a LiveKit room for a session.

    This task is scheduled to run T-30s before session start time.

    Args:
        session_id: Session UUID

    Returns:
        Room info dict with name and sid
    """
    logger.info(f"Creating LiveKit room for session {session_id}")

    # Fetch session from database
    supabase = get_supabase()
    result = supabase.table("sessions").select("*").eq("id", session_id).execute()

    if not result.data:
        logger.error(f"Session {session_id} not found")
        return {"error": "Session not found"}

    session = result.data[0]
    room_name = session["livekit_room_name"]
    mode = TableMode(session.get("mode", "forced_audio"))

    # Create room via LiveKit service
    livekit_service = LiveKitService()

    async def _create():
        try:
            room_info = await livekit_service.create_room(room_name, mode)
            logger.info(f"Created room {room_name} for session {session_id}")
            return room_info
        finally:
            await livekit_service.close()

    room_info = run_async(_create())

    # Update session with room creation timestamp
    supabase.table("sessions").update(
        {"livekit_room_created_at": "now()"}
    ).eq("id", session_id).execute()

    return room_info


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(LiveKitServiceError,),
)
def cleanup_ended_session(self, session_id: str) -> dict:
    """
    Clean up a LiveKit room after session ends.

    This task is scheduled to run ROOM_CLEANUP_DELAY_MINUTES after session end.

    Args:
        session_id: Session UUID

    Returns:
        Dict with cleanup status
    """
    logger.info(f"Cleaning up LiveKit room for session {session_id}")

    # Fetch session from database
    supabase = get_supabase()
    result = supabase.table("sessions").select("*").eq("id", session_id).execute()

    if not result.data:
        logger.warning(f"Session {session_id} not found during cleanup")
        return {"status": "session_not_found"}

    session = result.data[0]
    room_name = session["livekit_room_name"]

    # Delete room via LiveKit service
    livekit_service = LiveKitService()

    async def _delete():
        try:
            await livekit_service.delete_room(room_name)
            logger.info(f"Deleted room {room_name} for session {session_id}")
            return True
        except LiveKitServiceError as e:
            logger.warning(f"Room {room_name} may already be deleted: {e}")
            return False
        finally:
            await livekit_service.close()

    deleted = run_async(_delete())

    # Update session with cleanup timestamp
    supabase.table("sessions").update(
        {"livekit_room_deleted_at": "now()"}
    ).eq("id", session_id).execute()

    return {"status": "cleaned_up" if deleted else "already_deleted", "room_name": room_name}


@celery_app.task
def log_livekit_event(event_type: str, event_data: dict) -> None:
    """
    Log a LiveKit webhook event for debugging/analytics.

    Args:
        event_type: Type of event (participant_joined, etc.)
        event_data: Event payload
    """
    logger.info(f"LiveKit event: {event_type} - {event_data}")
