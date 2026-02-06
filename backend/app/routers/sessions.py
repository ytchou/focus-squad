"""
Session router for table management and matching endpoints.

Endpoints:
- POST /quick-match: Quick match into next available session
- GET /upcoming: List upcoming sessions for user
- GET /{session_id}: Get session details
- POST /{session_id}/leave: Leave a session early (no refund)
- POST /{session_id}/cancel: Cancel before start (refund if >=1hr before)
- POST /{session_id}/rate: Rate a participant (Phase 3 - not implemented)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import AuthUser, require_auth_from_state
from app.core.constants import ROOM_CLEANUP_DELAY_MINUTES, ROOM_CREATION_LEAD_TIME_SECONDS
from app.models.session import (
    CancelSessionResponse,
    LeaveSessionRequest,
    LeaveSessionResponse,
    ParticipantInfo,
    ParticipantType,
    QuickMatchRequest,
    QuickMatchResponse,
    SessionFilters,
    SessionInfo,
    SessionPhase,
    TableMode,
    UpcomingSession,
    UpcomingSessionsResponse,
)
from app.services.analytics_service import AnalyticsService
from app.services.credit_service import (
    CreditService,
    InsufficientCreditsError,
    TransactionType,
)
from app.services.session_service import (
    AlreadyInSessionError,
    SessionFullError,
    SessionService,
)
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Dependency Injection
# =============================================================================


def get_session_service() -> SessionService:
    """Get SessionService instance."""
    return SessionService()


def get_credit_service() -> CreditService:
    """Get CreditService instance."""
    return CreditService()


def get_user_service() -> UserService:
    """Get UserService instance."""
    return UserService()


def get_analytics_service() -> AnalyticsService:
    """Get AnalyticsService instance."""
    from app.core.database import get_supabase

    return AnalyticsService(supabase=get_supabase())


# =============================================================================
# Helper Functions
# =============================================================================


def _build_session_info(session_data: dict, include_token: bool = False) -> SessionInfo:
    """Convert session data dict to SessionInfo response model."""
    participants = []
    for p in session_data.get("participants", []):
        user = p.get("users") if p.get("users") else {}
        participants.append(
            ParticipantInfo(
                id=p["id"],
                user_id=p.get("user_id"),
                participant_type=ParticipantType(p["participant_type"]),
                seat_number=p["seat_number"],
                username=user.get("username") if user else None,
                display_name=user.get("display_name") if user else None,
                avatar_config=user.get("avatar_config", {}) if user else {},
                joined_at=_parse_datetime(p["joined_at"]),
                is_active=p.get("left_at") is None,
                ai_companion_name=p.get("ai_companion_name"),
            )
        )

    return SessionInfo(
        id=session_data["id"],
        start_time=_parse_datetime(session_data["start_time"]),
        end_time=_parse_datetime(session_data["end_time"]),
        mode=TableMode(session_data["mode"]),
        topic=session_data.get("topic"),
        language=session_data.get("language", "en"),
        current_phase=SessionPhase(session_data["current_phase"]),
        phase_started_at=_parse_datetime(session_data.get("phase_started_at"))
        if session_data.get("phase_started_at")
        else None,
        participants=participants,
        available_seats=session_data.get("available_seats", 4 - len(participants)),
        livekit_room_name=session_data["livekit_room_name"],
    )


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO datetime string to datetime object."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # Handle Z suffix
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/quick-match", response_model=QuickMatchResponse)
async def quick_match(
    request: QuickMatchRequest,
    user: AuthUser = Depends(require_auth_from_state),
    session_service: SessionService = Depends(get_session_service),
    credit_service: CreditService = Depends(get_credit_service),
    user_service: UserService = Depends(get_user_service),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    """
    Quick match into the next available session slot.

    Flow:
    1. Validate user exists and is not banned
    2. Check credit balance >= 1
    3. Calculate next time slot (:00 or :30)
    4. Find or create matching session
    5. Add user as participant
    6. Deduct 1 credit
    7. Generate LiveKit token
    8. Return session details
    """
    # Get user profile
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user is banned
    if profile.banned_until and profile.banned_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=403,
            detail=f"Account suspended until {profile.banned_until.isoformat()}",
        )

    # Check credit balance
    try:
        if not credit_service.has_sufficient_credits(profile.id, amount=1):
            raise HTTPException(
                status_code=402,
                detail="Insufficient credits. You need at least 1 credit to join a session.",
            )
    except Exception:
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits. You need at least 1 credit to join a session.",
        )

    # Calculate next time slot
    next_slot = session_service.calculate_next_slot()

    # Check if user already has a session at this time slot
    existing_session = session_service.get_user_session_at_time(profile.id, next_slot)
    if existing_session:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "You already have a session at this time slot",
                "existing_session_id": existing_session["id"],
                "start_time": existing_session["start_time"],
            },
        )

    # Get filters (default if not provided)
    filters = request.filters or SessionFilters()

    # Find or create session and add participant
    try:
        session_data, seat_number = session_service.find_or_create_session(
            filters=filters,
            start_time=next_slot,
            user_id=profile.id,
        )

        # Schedule LiveKit room creation and cleanup tasks
        _schedule_livekit_tasks(session_data, next_slot)

    except AlreadyInSessionError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "You are already in a session at this time slot",
                "existing_session_id": e.session_id,
            },
        )
    except SessionFullError:
        raise HTTPException(
            status_code=409,
            detail="No available sessions found. Please try again.",
        )

    # Deduct credit
    try:
        credit_service.deduct_credit(
            user_id=profile.id,
            amount=1,
            transaction_type=TransactionType.SESSION_JOIN,
            description=f"Joined session {session_data['id']}",
        )
    except InsufficientCreditsError:
        # Rollback: remove participant if credit deduction fails
        session_service.remove_participant(session_data["id"], profile.id)
        raise HTTPException(
            status_code=402,
            detail="Insufficient credits",
        )

    # Generate LiveKit token
    livekit_token = session_service.generate_livekit_token(
        room_name=session_data["livekit_room_name"],
        participant_identity=profile.id,
        participant_name=profile.display_name or profile.username,
    )

    # Build response
    session_info = _build_session_info(session_data)

    # Calculate wait time
    now = datetime.now(timezone.utc)
    matched_session_start = _parse_datetime(session_data["start_time"])
    wait_seconds = (matched_session_start - now).total_seconds()
    wait_minutes = max(0, int(wait_seconds / 60))  # Round down, never negative
    is_immediate = wait_minutes < 1

    # Track analytics event (fire-and-forget)
    await analytics_service.track_event(
        user_id=profile.id,
        session_id=session_data["id"],
        event_type="waiting_room_entered",
        metadata={
            "wait_minutes": wait_minutes,
            "is_immediate": is_immediate,
            "mode": session_data["mode"],
        },
    )

    return QuickMatchResponse(
        session=session_info,
        livekit_token=livekit_token,
        seat_number=seat_number,
        credit_deducted=True,
        wait_minutes=wait_minutes,
        is_immediate=is_immediate,
    )


@router.get("/upcoming", response_model=UpcomingSessionsResponse)
async def get_upcoming_sessions(
    user: AuthUser = Depends(require_auth_from_state),
    session_service: SessionService = Depends(get_session_service),
    user_service: UserService = Depends(get_user_service),
):
    """
    Get upcoming sessions the user is matched to.

    Returns sessions where:
    - User is an active participant (not left)
    - Session has not ended
    """
    # Get user profile
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's sessions
    sessions_data = session_service.get_user_sessions(profile.id)

    # Convert to response models
    sessions = []
    for s in sessions_data:
        sessions.append(
            UpcomingSession(
                id=s["id"],
                start_time=_parse_datetime(s["start_time"]),
                end_time=_parse_datetime(s["end_time"]),
                mode=TableMode(s["mode"]),
                topic=s.get("topic"),
                language=s.get("language", "en"),
                current_phase=SessionPhase(s["current_phase"]),
                participant_count=s.get("participant_count", 0),
                my_seat_number=s.get("my_seat_number", 1),
            )
        )

    return UpcomingSessionsResponse(sessions=sessions)


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    user: AuthUser = Depends(require_auth_from_state),
    session_service: SessionService = Depends(get_session_service),
    user_service: UserService = Depends(get_user_service),
):
    """
    Get session details.

    User must be a participant in the session to view details.
    """
    # Get user profile
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # Get session
    session_data = session_service.get_session_by_id(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify user is a participant
    if not session_service.is_participant(session_data, profile.id):
        raise HTTPException(
            status_code=403,
            detail="You are not a participant in this session",
        )

    return _build_session_info(session_data)


@router.post("/{session_id}/leave", response_model=LeaveSessionResponse)
async def leave_session(
    session_id: str,
    request: LeaveSessionRequest = LeaveSessionRequest(),
    user: AuthUser = Depends(require_auth_from_state),
    session_service: SessionService = Depends(get_session_service),
    user_service: UserService = Depends(get_user_service),
):
    """
    Leave a session early.

    Note: Credits are NOT refunded for early leave (user's choice).
    User will NOT earn essence for this session.
    """
    # Get user profile
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # Get session
    session_data = session_service.get_session_by_id(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify user is a participant
    if not session_service.is_participant(session_data, profile.id):
        raise HTTPException(
            status_code=403,
            detail="You are not a participant in this session",
        )

    # Remove participant
    session_service.remove_participant(
        session_id=session_id,
        user_id=profile.id,
        reason=request.reason,
    )

    return LeaveSessionResponse(status="left", session_id=session_id)


@router.post("/{session_id}/cancel", response_model=CancelSessionResponse)
async def cancel_session(
    session_id: str,
    user: AuthUser = Depends(require_auth_from_state),
    session_service: SessionService = Depends(get_session_service),
    credit_service: CreditService = Depends(get_credit_service),
    user_service: UserService = Depends(get_user_service),
):
    """
    Cancel a session booking before it starts.

    Refund policy (per design doc):
    - Cancel >=1 hour before session start: FULL REFUND
    - Cancel <1 hour before session start: NO REFUND
    - Session already started: Use /leave instead (no refund)
    """
    # Get user profile
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # Get session
    session_data = session_service.get_session_by_id(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify user is a participant
    participant = session_service.get_participant(session_data, profile.id)
    if not participant:
        raise HTTPException(
            status_code=403,
            detail="You are not a participant in this session",
        )

    # Check if session has already started
    start_time = _parse_datetime(session_data["start_time"])
    now = datetime.now(timezone.utc)

    if now >= start_time:
        raise HTTPException(
            status_code=400,
            detail="Session has already started. Use /leave endpoint instead.",
        )

    # Calculate time until session starts
    time_until_start = start_time - now
    refund_eligible = time_until_start >= timedelta(hours=1)

    # Remove participant
    session_service.remove_participant(
        session_id=session_id,
        user_id=profile.id,
        reason="cancelled",
    )

    # Process refund if eligible
    credit_refunded = False
    if refund_eligible:
        transaction = credit_service.refund_credit(
            user_id=profile.id,
            session_id=session_id,
            participant_id=participant["id"],
        )
        credit_refunded = transaction is not None

    # Build response message
    if credit_refunded:
        message = "Session cancelled. Credit refunded to your account."
    elif refund_eligible:
        message = "Session cancelled. Credit was already refunded."
    else:
        minutes_until = int(time_until_start.total_seconds() / 60)
        message = f"Session cancelled. No refund (cancelled {minutes_until} minutes before start, minimum 60 required)."

    return CancelSessionResponse(
        status="cancelled",
        session_id=session_id,
        credit_refunded=credit_refunded,
        message=message,
    )


@router.post("/{session_id}/rate")
async def rate_participant(session_id: str, participant_id: str, rating: str):
    """
    Rate a session participant (green/red/skip).

    NOT IMPLEMENTED - This belongs to Phase 3: Peer Review System.
    """
    raise HTTPException(status_code=501, detail="Not implemented - Phase 3")


# =============================================================================
# Task Scheduling
# =============================================================================


def _schedule_livekit_tasks(session_data: dict, start_time: datetime) -> None:
    """
    Schedule Celery tasks for LiveKit room management and session setup.

    Tasks:
    1. Room creation: T-30s before session start
    2. Fill empty seats with AI: T+0 (at session start)
    3. Room cleanup: 5 minutes after session end

    Args:
        session_data: Session dict with id, end_time, etc.
        start_time: Session start time
    """
    try:
        from app.tasks.livekit_tasks import (
            cleanup_ended_session,
            create_livekit_room,
            fill_empty_seats_with_ai,
        )

        session_id = session_data["id"]
        end_time = _parse_datetime(session_data["end_time"])

        # Calculate task execution times
        room_creation_time = start_time - timedelta(seconds=ROOM_CREATION_LEAD_TIME_SECONDS)
        ai_fill_time = start_time  # T+0: Fill AI companions right at session start
        cleanup_time = end_time + timedelta(minutes=ROOM_CLEANUP_DELAY_MINUTES)

        now = datetime.now(timezone.utc)

        # Schedule room creation (if not already past)
        if room_creation_time > now:
            create_livekit_room.apply_async(
                args=[session_id],
                eta=room_creation_time,
                task_id=f"create-room-{session_id}",
            )
            logger.info(f"Scheduled room creation for session {session_id} at {room_creation_time}")
        else:
            # Create immediately if we're past the scheduled time
            create_livekit_room.delay(session_id)
            logger.info(f"Creating room immediately for session {session_id}")

        # Schedule AI companion fill (if not already past)
        if ai_fill_time > now:
            fill_empty_seats_with_ai.apply_async(
                args=[session_id],
                eta=ai_fill_time,
                task_id=f"fill-ai-{session_id}",
            )
            logger.info(f"Scheduled AI companion fill for session {session_id} at {ai_fill_time}")
        else:
            # Fill immediately if we're past the scheduled time
            fill_empty_seats_with_ai.delay(session_id)
            logger.info(f"Filling AI companions immediately for session {session_id}")

        # Schedule cleanup
        cleanup_ended_session.apply_async(
            args=[session_id],
            eta=cleanup_time,
            task_id=f"cleanup-session-{session_id}",
        )
        logger.info(f"Scheduled cleanup for session {session_id} at {cleanup_time}")

    except Exception as e:
        # Don't fail the request if task scheduling fails
        # Room will be auto-created by LiveKit when first participant joins
        logger.warning(f"Failed to schedule LiveKit tasks: {e}")


# =============================================================================
# Debug Endpoints (Admin Only)
# =============================================================================


@router.post("/{session_id}/debug/complete")
async def debug_complete_session(
    session_id: str,
    auth_user: AuthUser = Depends(require_auth_from_state),
) -> dict:
    """
    [DEBUG/ADMIN ONLY] Trigger session completion stats update.

    This endpoint bypasses the scheduled cleanup task and immediately
    updates user stats as if the session completed normally.

    Only available to users with admin tier.
    """
    from app.core.database import get_supabase
    from app.models.credit import UserTier

    supabase = get_supabase()

    # Verify user is admin tier
    user_profile = UserService(supabase=supabase).get_by_auth_id(auth_user.user_id)
    credit_record = (
        supabase.table("credits").select("tier").eq("user_id", user_profile.id).execute()
    )

    user_tier = credit_record.data[0]["tier"] if credit_record.data else "free"
    if user_tier != UserTier.ADMIN.value:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Verify session exists
    session_result = supabase.table("sessions").select("id").eq("id", session_id).execute()
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get all human participants who haven't left early
    participants = (
        supabase.table("session_participants")
        .select("user_id")
        .eq("session_id", session_id)
        .eq("participant_type", "human")
        .is_("left_at", "null")
        .execute()
    )

    if not participants.data:
        return {"message": "No participants to update", "updated": 0}

    # Update stats for each participant
    user_service = UserService(supabase=supabase)
    focus_minutes = 45  # Standard session focus time

    updated = 0
    for participant in participants.data:
        user_id = participant.get("user_id")
        if user_id:
            try:
                user_service.record_session_completion(user_id, focus_minutes)
                updated += 1
                logger.info(f"[DEBUG] Updated stats for user {user_id}")
            except Exception as e:
                logger.error(f"[DEBUG] Failed to update stats for user {user_id}: {e}")

    return {"message": f"Updated stats for {updated} participants", "updated": updated}
