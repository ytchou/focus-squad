"""
Pydantic models for the Session Board reflection system.

Design doc: output/plan/2026-02-08-session-board-design.md

Reflections are structured text entries prompted at phase transitions
(setup, break, social). They are persisted to power a personal Session Diary.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


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
    content: str = Field(..., min_length=1, max_length=500)


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
    reflections: list[DiaryReflection]


class DiaryResponse(BaseModel):
    """Paginated diary response."""
    items: list[DiaryEntry]
    total: int
    page: int
    per_page: int


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
