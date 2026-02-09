"""
Analytics router for tracking session behavior events.

Endpoints:
- POST /track: Track an analytics event (fire-and-forget)
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.core.auth import AuthUser, require_auth_from_state
from app.core.rate_limit import limiter
from app.services.analytics_service import AnalyticsService
from app.services.user_service import UserService

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class TrackEventRequest(BaseModel):
    """Request model for tracking an analytics event."""

    event_type: str
    session_id: UUID
    metadata: Optional[dict] = None


class TrackEventResponse(BaseModel):
    """Response model for track event endpoint."""

    success: bool


# =============================================================================
# Dependency Injection
# =============================================================================


def get_analytics_service() -> AnalyticsService:
    """Get AnalyticsService instance."""
    from app.core.database import get_supabase

    return AnalyticsService(supabase=get_supabase())


def get_user_service() -> UserService:
    """Get UserService instance."""
    return UserService()


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/track", response_model=TrackEventResponse)
@limiter.limit("60/minute")
async def track_event(
    request: Request,
    track_request: TrackEventRequest,
    user: AuthUser = Depends(require_auth_from_state),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    user_service: UserService = Depends(get_user_service),
):
    """Track an analytics event (fire-and-forget).

    Event types:
        - waiting_room_resumed: User resumed waiting room after page reload
        - waiting_room_abandoned: User left early (before session start)
        - session_joined_from_waiting_room: User successfully joined session

    Note:
        This endpoint always returns success=True, even if tracking fails.
        Analytics failures should not break user flow.
    """
    try:
        # Look up user's internal ID from auth_id
        profile = user_service.get_user_by_auth_id(user.auth_id)
        if profile:
            await analytics_service.track_event(
                user_id=profile.id,
                session_id=track_request.session_id,
                event_type=track_request.event_type,
                metadata=track_request.metadata,
            )
    except Exception:
        # Analytics failures should not break user flow
        pass

    return TrackEventResponse(success=True)
