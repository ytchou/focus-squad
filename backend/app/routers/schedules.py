"""
Recurring schedule management endpoints.

Handles:
- GET / - List user's recurring schedules
- POST / - Create a recurring schedule (Unlimited plan only)
- PATCH /{schedule_id} - Update a recurring schedule
- DELETE /{schedule_id} - Delete a recurring schedule
"""

import logging

from fastapi import APIRouter, Depends, Request

from app.core.auth import AuthUser, require_auth_from_state
from app.core.rate_limit import limiter
from app.models.schedule import (
    RecurringScheduleCreate,
    RecurringScheduleUpdate,
    ScheduleCreateResponse,
    ScheduleDeleteResponse,
    ScheduleListResponse,
    ScheduleUpdateResponse,
)
from app.services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Dependency Injection
# =============================================================================


def get_schedule_service() -> ScheduleService:
    """Get ScheduleService instance."""
    return ScheduleService()


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/", response_model=ScheduleListResponse)
async def list_schedules(
    user: AuthUser = Depends(require_auth_from_state),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleListResponse:
    """
    List the current user's recurring schedules.

    Returns all active recurring schedules with their day/time configurations.
    """
    schedules = schedule_service.list_schedules(user.user_id)
    return ScheduleListResponse(schedules=schedules)


@router.post("/", response_model=ScheduleCreateResponse, status_code=201)
@limiter.limit("10/minute")
async def create_schedule(
    request: Request,
    body: RecurringScheduleCreate,
    user: AuthUser = Depends(require_auth_from_state),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleCreateResponse:
    """
    Create a new recurring schedule.

    Only available for Unlimited plan users. Schedules auto-book
    table seats at the configured day/time each week.
    """
    schedule = schedule_service.create_schedule(user.user_id, body)
    return ScheduleCreateResponse(schedule=schedule)


@router.patch("/{schedule_id}", response_model=ScheduleUpdateResponse)
@limiter.limit("10/minute")
async def update_schedule(
    request: Request,
    schedule_id: str,
    body: RecurringScheduleUpdate,
    user: AuthUser = Depends(require_auth_from_state),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleUpdateResponse:
    """
    Update an existing recurring schedule.

    Only the schedule owner can update it.
    """
    schedule = schedule_service.update_schedule(schedule_id, user.user_id, body)
    return ScheduleUpdateResponse(schedule=schedule)


@router.delete("/{schedule_id}", response_model=ScheduleDeleteResponse)
@limiter.limit("10/minute")
async def delete_schedule(
    request: Request,
    schedule_id: str,
    user: AuthUser = Depends(require_auth_from_state),
    schedule_service: ScheduleService = Depends(get_schedule_service),
) -> ScheduleDeleteResponse:
    """
    Delete a recurring schedule.

    Only the schedule owner can delete it.
    """
    schedule_service.delete_schedule(schedule_id, user.user_id)
    return ScheduleDeleteResponse(success=True)
