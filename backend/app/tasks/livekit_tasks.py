"""
Celery tasks for LiveKit room management.

Handles:
- Scheduled room creation (T-30s before session)
- Room cleanup after sessions end
- Referral bonus awards on session completion
"""

import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.database import get_supabase
from app.models.session import TableMode
from app.services.credit_service import CreditService
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
    supabase.table("sessions").update({"livekit_room_created_at": "now()"}).eq(
        "id", session_id
    ).execute()

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
    Also triggers referral bonus awards for participants who completed their first session.

    Args:
        session_id: Session UUID

    Returns:
        Dict with cleanup status and referral awards
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
    supabase.table("sessions").update({"livekit_room_deleted_at": "now()"}).eq(
        "id", session_id
    ).execute()

    # Award referral bonuses for participants who completed their first session
    referrals_awarded = _award_referral_bonuses(supabase, session_id)

    return {
        "status": "cleaned_up" if deleted else "already_deleted",
        "room_name": room_name,
        "referrals_awarded": referrals_awarded,
    }


def _award_referral_bonuses(supabase, session_id: str) -> int:
    """
    Award referral bonuses to participants who completed their first session.

    Args:
        supabase: Supabase client
        session_id: Session UUID

    Returns:
        Count of referral bonuses awarded
    """
    # Get all human participants who completed the session (not left early)
    participants = (
        supabase.table("session_participants")
        .select("user_id")
        .eq("session_id", session_id)
        .eq("participant_type", "human")
        .is_("left_at", "null")  # Didn't leave early
        .execute()
    )

    if not participants.data:
        return 0

    credit_service = CreditService(supabase=supabase)
    awards = 0

    for participant in participants.data:
        user_id = participant.get("user_id")
        if not user_id:
            continue

        try:
            if credit_service.award_referral_bonus(user_id):
                awards += 1
                logger.info(f"Awarded referral bonus to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to award referral bonus to user {user_id}: {e}")

    return awards


@celery_app.task
def log_livekit_event(event_type: str, event_data: dict) -> None:
    """
    Log a LiveKit webhook event for debugging/analytics.

    Args:
        event_type: Type of event (participant_joined, etc.)
        event_data: Event payload
    """
    logger.info(f"LiveKit event: {event_type} - {event_data}")
