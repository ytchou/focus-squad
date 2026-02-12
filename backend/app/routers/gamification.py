"""
Gamification API endpoints (Phase 4B: Diary Integration).

Handles:
- GET /streak - Current week's session streak
- GET /mood - Companion mood baseline
- GET /timeline - Growth timeline snapshots
- POST /timeline/snapshot - Upload room snapshot
- GET /timeline/milestones - Check pending milestones
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.auth import AuthUser, require_auth_from_state
from app.core.rate_limit import limiter
from app.models.gamification import (
    MoodResponse,
    SnapshotUploadRequest,
    SnapshotUploadResponse,
    TimelineResponse,
    WeeklyStreakResponse,
)
from app.services.mood_service import MoodService
from app.services.streak_service import StreakService
from app.services.timeline_service import TimelineService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_streak_service() -> StreakService:
    return StreakService()


def get_mood_service() -> MoodService:
    return MoodService()


def get_timeline_service() -> TimelineService:
    return TimelineService()


def get_user_service() -> UserService:
    return UserService()


# =============================================================================
# Streak Endpoints
# =============================================================================


@router.get("/streak", response_model=WeeklyStreakResponse)
@limiter.limit("60/minute")
async def get_weekly_streak(
    request: Request,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    streak_service: StreakService = Depends(get_streak_service),
) -> WeeklyStreakResponse:
    """Get current week's session streak status and bonus progress."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return streak_service.get_weekly_streak(profile.id)


# =============================================================================
# Mood Endpoints
# =============================================================================


@router.get("/mood", response_model=MoodResponse)
@limiter.limit("60/minute")
async def get_companion_mood(
    request: Request,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    mood_service: MoodService = Depends(get_mood_service),
) -> MoodResponse:
    """Get the companion's mood baseline from recent diary entries."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return mood_service.compute_mood(profile.id)


# =============================================================================
# Timeline Endpoints
# =============================================================================


@router.get("/timeline", response_model=TimelineResponse)
@limiter.limit("60/minute")
async def get_timeline(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    timeline_service: TimelineService = Depends(get_timeline_service),
) -> TimelineResponse:
    """Get paginated growth timeline of room snapshots."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return timeline_service.get_timeline(profile.id, page=page, per_page=per_page)


@router.post("/timeline/snapshot", response_model=SnapshotUploadResponse)
@limiter.limit("10/minute")
async def upload_snapshot(
    request: Request,
    body: SnapshotUploadRequest,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    timeline_service: TimelineService = Depends(get_timeline_service),
) -> SnapshotUploadResponse:
    """Upload a room snapshot for a milestone event."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    session_count = _get_user_session_count(timeline_service, profile.id)
    return timeline_service.upload_snapshot(profile.id, body, session_count=session_count)


@router.get("/timeline/milestones", response_model=list[str])
@limiter.limit("30/minute")
async def check_milestones(
    request: Request,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    timeline_service: TimelineService = Depends(get_timeline_service),
) -> list[str]:
    """Check which milestones the user has earned but not yet captured."""
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return timeline_service.check_milestones(profile.id)


def _get_user_session_count(timeline_service: TimelineService, user_id: str) -> int:
    """Helper to get user's total session count for snapshot metadata."""
    result = (
        timeline_service.supabase.table("sessions")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    return len(result.data) if result.data else 0
