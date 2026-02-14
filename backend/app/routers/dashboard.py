"""
Dashboard init batch endpoint.

Aggregates multiple dashboard data sources into a single response
to reduce HTTP round-trips on dashboard load (5 calls → 1).
"""

import asyncio
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.core.auth import AuthUser, require_auth_from_state
from app.core.rate_limit import limiter
from app.models.gamification import WeeklyStreakResponse
from app.models.partner import InvitationInfo, InvitationStatus
from app.models.rating import PendingRatingsResponse
from app.models.session import TimeSlotInfo, UpcomingSlotsResponse
from app.services.rating_service import RatingService
from app.services.session_service import SessionService
from app.services.streak_service import StreakService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


class DashboardInitResponse(BaseModel):
    """Combined response for dashboard initialization."""

    pending_ratings: PendingRatingsResponse
    invitations: list[InvitationInfo]
    streak: WeeklyStreakResponse
    upcoming_slots: UpcomingSlotsResponse


def get_user_service() -> UserService:
    return UserService()


def get_rating_service() -> RatingService:
    return RatingService()


def get_session_service() -> SessionService:
    return SessionService()


def get_streak_service() -> StreakService:
    return StreakService()


def _build_invitations(
    raw_invitations: list[dict[str, Any]],
    user_service: UserService,
) -> list[InvitationInfo]:
    """Transform raw invitation data into InvitationInfo models."""
    invitations = []
    for inv in raw_invitations:
        session = inv.get("sessions", {})
        inviter = user_service.get_public_profile(inv["inviter_id"])
        inviter_name = inviter.display_name or inviter.username if inviter else "Unknown"

        invitations.append(
            InvitationInfo(
                id=inv["id"],
                session_id=inv["session_id"],
                inviter_id=inv["inviter_id"],
                inviter_name=inviter_name,
                time_slot=session.get("start_time", ""),
                mode=session.get("mode", "forced_audio"),
                topic=session.get("topic"),
                status=InvitationStatus(inv["status"]),
                created_at=inv["created_at"],
            )
        )
    return invitations


def _fetch_pending_ratings(rating_service: RatingService, user_id: str) -> PendingRatingsResponse:
    """Fetch pending ratings (sync, for thread execution)."""
    pending = rating_service.get_pending_ratings(user_id)
    return PendingRatingsResponse(
        has_pending=pending is not None,
        pending=pending,
    )


def _fetch_invitations(
    session_service: SessionService,
    user_service: UserService,
    user_id: str,
) -> list[InvitationInfo]:
    """Fetch and transform invitations (sync, for thread execution)."""
    raw = session_service.get_pending_invitations(user_id)
    return _build_invitations(raw, user_service)


def _fetch_streak(streak_service: StreakService, user_id: str) -> WeeklyStreakResponse:
    """Fetch weekly streak (sync, for thread execution)."""
    return streak_service.get_weekly_streak(user_id)


def _fetch_upcoming_slots(
    session_service: SessionService,
    user_id: str,
    mode: Optional[str],
) -> UpcomingSlotsResponse:
    """Fetch upcoming slots (sync, for thread execution)."""
    slot_times = session_service.calculate_upcoming_slots()
    queue_counts = session_service.get_slot_queue_counts(slot_times, mode=mode)
    estimates = session_service.get_slot_estimates(slot_times)
    user_slots = session_service.get_user_sessions_at_slots(user_id, slot_times)

    slots = []
    for slot_time in slot_times:
        iso = slot_time.isoformat()
        slots.append(
            TimeSlotInfo(
                start_time=slot_time,
                queue_count=queue_counts.get(iso, 0),
                estimated_count=estimates.get(iso, 0),
                has_user_session=iso in user_slots,
            )
        )
    return UpcomingSlotsResponse(slots=slots)


@router.get("/init", response_model=DashboardInitResponse)
@limiter.limit("30/minute")
async def dashboard_init(
    request: Request,
    mode: Optional[str] = Query(None, description="Filter slots by mode: forced_audio or quiet"),
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
    rating_service: RatingService = Depends(get_rating_service),
    session_service: SessionService = Depends(get_session_service),
    streak_service: StreakService = Depends(get_streak_service),
):
    """
    Batch endpoint for dashboard initialization.

    Returns pending ratings, invitations, weekly streak, and upcoming slots
    in a single response, reducing 4 HTTP round-trips to 1.
    """
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    # Run all queries in parallel via thread pool
    pending_ratings, invitations, streak, upcoming_slots = await asyncio.gather(
        asyncio.to_thread(_fetch_pending_ratings, rating_service, profile.id),
        asyncio.to_thread(_fetch_invitations, session_service, user_service, profile.id),
        asyncio.to_thread(_fetch_streak, streak_service, profile.id),
        asyncio.to_thread(_fetch_upcoming_slots, session_service, profile.id, mode),
    )

    return DashboardInitResponse(
        pending_ratings=pending_ratings,
        invitations=invitations,
        streak=streak,
        upcoming_slots=upcoming_slots,
    )
