"""
Recurring schedule models for accountability partners.

Aligned with design doc: output/plan/2026-02-12-accountability-partners-design.md
"""

from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.core.constants import (
    MAX_PRIVATE_TABLE_SEATS,
    MIN_PRIVATE_TABLE_SEATS,
    SCHEDULE_LABEL_MAX_LENGTH,
    TOPIC_MAX_LENGTH,
)

# ===========================================
# Request Models
# ===========================================


class RecurringScheduleCreate(BaseModel):
    """Create a recurring schedule (Unlimited plan only)."""

    partner_ids: list[str] = Field(..., min_length=1, max_length=3)
    days_of_week: list[int] = Field(..., min_length=1, max_length=7)
    slot_time: time
    timezone: str = "Asia/Taipei"
    label: Optional[str] = Field(None, max_length=SCHEDULE_LABEL_MAX_LENGTH)
    table_mode: str = "forced_audio"
    max_seats: int = Field(
        MAX_PRIVATE_TABLE_SEATS,
        ge=MIN_PRIVATE_TABLE_SEATS,
        le=MAX_PRIVATE_TABLE_SEATS,
    )
    fill_ai: bool = True
    topic: Optional[str] = Field(None, max_length=TOPIC_MAX_LENGTH)

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, v: list[int]) -> list[int]:
        for day in v:
            if day < 0 or day > 6:
                raise ValueError(f"Day of week must be 0-6 (Sun-Sat), got {day}")
        return sorted(set(v))

    @field_validator("table_mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("forced_audio", "quiet"):
            raise ValueError("Table mode must be 'forced_audio' or 'quiet'")
        return v


class RecurringScheduleUpdate(BaseModel):
    """Partial update for a recurring schedule."""

    partner_ids: Optional[list[str]] = Field(None, min_length=1, max_length=3)
    days_of_week: Optional[list[int]] = Field(None, min_length=1, max_length=7)
    slot_time: Optional[time] = None
    timezone: Optional[str] = None
    label: Optional[str] = Field(None, max_length=SCHEDULE_LABEL_MAX_LENGTH)
    table_mode: Optional[str] = None
    max_seats: Optional[int] = Field(None, ge=MIN_PRIVATE_TABLE_SEATS, le=MAX_PRIVATE_TABLE_SEATS)
    fill_ai: Optional[bool] = None
    topic: Optional[str] = Field(None, max_length=TOPIC_MAX_LENGTH)
    is_active: Optional[bool] = None

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        if v is None:
            return v
        for day in v:
            if day < 0 or day > 6:
                raise ValueError(f"Day of week must be 0-6 (Sun-Sat), got {day}")
        return sorted(set(v))

    @field_validator("table_mode")
    @classmethod
    def validate_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ("forced_audio", "quiet"):
            raise ValueError("Table mode must be 'forced_audio' or 'quiet'")
        return v


# ===========================================
# Response Models
# ===========================================


class RecurringScheduleInfo(BaseModel):
    """Information about a recurring schedule."""

    id: str
    label: Optional[str] = None
    creator_id: str
    partner_ids: list[str]
    partner_names: list[str] = Field(default_factory=list)
    days_of_week: list[int]
    slot_time: str  # HH:MM format
    timezone: str
    table_mode: str
    max_seats: int
    fill_ai: bool
    topic: Optional[str] = None
    is_active: bool
    created_at: datetime


class ScheduleListResponse(BaseModel):
    """Response for listing recurring schedules."""

    schedules: list[RecurringScheduleInfo]


class ScheduleCreateResponse(BaseModel):
    """Response after creating a schedule."""

    schedule: RecurringScheduleInfo
    message: str = "Recurring schedule created"


class ScheduleUpdateResponse(BaseModel):
    """Response after updating a schedule."""

    schedule: RecurringScheduleInfo
    message: str = "Schedule updated"


class ScheduleDeleteResponse(BaseModel):
    """Response after deleting a schedule."""

    message: str = "Schedule deleted"


# ===========================================
# Exception Classes
# ===========================================


class ScheduleServiceError(Exception):
    """Base exception for schedule service errors."""

    pass


class ScheduleNotFoundError(ScheduleServiceError):
    """Schedule not found."""

    pass


class SchedulePermissionError(ScheduleServiceError):
    """User does not have permission (not Unlimited plan)."""

    pass


class ScheduleOwnershipError(ScheduleServiceError):
    """User is not the creator of this schedule."""

    pass


class ScheduleLimitError(ScheduleServiceError):
    """Maximum number of recurring schedules reached."""

    pass
