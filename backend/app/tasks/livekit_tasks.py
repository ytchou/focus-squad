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

    # Update user stats for participants who completed the session
    stats_updated = _update_user_session_stats(supabase, session_id, session)

    # Award referral bonuses for participants who completed their first session
    referrals_awarded = _award_referral_bonuses(supabase, session_id)

    return {
        "status": "cleaned_up" if deleted else "already_deleted",
        "room_name": room_name,
        "stats_updated": stats_updated,
        "referrals_awarded": referrals_awarded,
    }


def _update_user_session_stats(supabase, session_id: str, session: dict) -> int:
    """
    Update user stats (session_count, total_focus_minutes) after session completion.

    Args:
        supabase: Supabase client
        session_id: Session UUID
        session: Session dict with start_time, end_time

    Returns:
        Count of users whose stats were updated
    """

    from app.services.user_service import UserService

    # Calculate focus minutes (session duration minus setup/social time)
    # Standard session: 55 min total, but focus time is work1 (25) + work2 (20) = 45 min
    focus_minutes = 45

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

    user_service = UserService(supabase=supabase)
    updated = 0

    for participant in participants.data:
        user_id = participant.get("user_id")
        if not user_id:
            continue

        try:
            user_service.record_session_completion(user_id, focus_minutes)
            updated += 1
            logger.info(f"Updated session stats for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to update stats for user {user_id}: {e}")

    return updated


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


@celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
def fill_empty_seats_with_ai(self, session_id: str) -> dict:
    """
    Fill empty seats with AI companions at session start.

    This task is scheduled to run at T+0 (session start time).
    Checks how many human participants are present and fills remaining
    seats (up to 4) with AI companions.

    Args:
        session_id: Session UUID

    Returns:
        Dict with count of AI companions added
    """
    from app.services.session_service import SessionService

    logger.info(f"Filling empty seats with AI companions for session {session_id}")

    supabase = get_supabase()
    session_service = SessionService(supabase=supabase)

    # Get current participant count
    participants = (
        supabase.table("session_participants")
        .select("id")
        .eq("session_id", session_id)
        .is_("left_at", "null")
        .execute()
    )

    current_count = len(participants.data) if participants.data else 0
    max_seats = 4

    if current_count >= max_seats:
        logger.info(f"Session {session_id} already has {current_count} participants, no AI needed")
        return {"ai_companions_added": 0}

    # Add AI companions to fill remaining seats
    ai_needed = max_seats - current_count
    ai_companions = session_service.add_ai_companions(session_id, ai_needed)

    logger.info(f"Added {len(ai_companions)} AI companions to session {session_id}")

    return {"ai_companions_added": len(ai_companions)}
