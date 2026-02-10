"""
Pydantic models for the Session Board reflection system.

Design doc: output/plan/2026-02-08-session-board-design.md

Reflections are structured text entries prompted at phase transitions
(setup, break, social). They are persisted to power a personal Session Diary.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import DIARY_NOTE_MAX_LENGTH, REFLECTION_MAX_LENGTH

# =============================================================================
# Enums
# =============================================================================


class ReflectionPhase(str, Enum):
    """Session phases where reflections are prompted."""

    SETUP = "setup"
    BREAK = "break"
    SOCIAL = "social"


# =============================================================================
# Request Models
# =============================================================================


class SaveReflectionRequest(BaseModel):
    """Request to save a reflection for a session phase."""

    phase: ReflectionPhase
    content: str = Field(..., min_length=1, max_length=REFLECTION_MAX_LENGTH)


# =============================================================================
# Response Models
# =============================================================================


class ReflectionResponse(BaseModel):
    """A single reflection entry."""

    id: str
    session_id: str
    user_id: str
    display_name: Optional[str] = None
    phase: ReflectionPhase
    content: str
    created_at: datetime
    updated_at: datetime


class SessionReflectionsResponse(BaseModel):
    """All reflections for a session (from all participants)."""

    reflections: list[ReflectionResponse]


class DiaryReflection(BaseModel):
    """A single reflection within a diary entry."""

    phase: ReflectionPhase
    content: str
    created_at: datetime


class DiaryEntry(BaseModel):
    """A session's reflections grouped for the diary view."""

    session_id: str
    session_date: datetime
    session_topic: Optional[str] = None
    focus_minutes: int = 0
    reflections: list[DiaryReflection]
    note: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class DiaryResponse(BaseModel):
    """Paginated diary response."""

    items: list[DiaryEntry]
    total: int
    page: int
    per_page: int


# =============================================================================
# Diary Note Models
# =============================================================================


class SaveDiaryNoteRequest(BaseModel):
    """Request to save/update a post-session diary note."""

    note: Optional[str] = Field(None, max_length=DIARY_NOTE_MAX_LENGTH)
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        from app.core.constants import DIARY_TAGS

        invalid = [tag for tag in v if tag not in DIARY_TAGS]
        if invalid:
            raise ValueError(f"Invalid tags: {invalid}")
        return v


class DiaryNoteResponse(BaseModel):
    """Response after saving a diary note."""

    session_id: str
    note: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DiaryStatsResponse(BaseModel):
    """Personal diary statistics."""

    current_streak: int
    weekly_focus_minutes: int
    total_sessions: int


# =============================================================================
# Internal / DB Models
# =============================================================================


class ReflectionRecord(BaseModel):
    """A reflection record as stored in the database."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    user_id: str
    phase: str
    content: str
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Exceptions
# =============================================================================


class ReflectionServiceError(Exception):
    """Base exception for reflection service errors."""

    pass


class NotSessionParticipantError(ReflectionServiceError):
    """User is not a participant in this session."""

    pass


class SessionNotFoundError(ReflectionServiceError):
    """Session does not exist."""

    pass
