"""
Analytics router for tracking session behavior events.

Endpoints:
- POST /track: Track an analytics event (fire-and-forget)
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import AuthUser, require_auth_from_state
from app.services.analytics_service import AnalyticsService

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
    return AnalyticsService()


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/track", response_model=TrackEventResponse)
async def track_event(
    request: TrackEventRequest,
    user: AuthUser = Depends(require_auth_from_state),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
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
    await analytics_service.track_event(
        user_id=user.id,
        session_id=request.session_id,
        event_type=request.event_type,
        metadata=request.metadata,
    )

    return TrackEventResponse(success=True)
