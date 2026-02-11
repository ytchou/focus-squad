"""
Pydantic models for session-related operations.

Models:
- Enums: TableMode, SessionPhase, ParticipantType
- Request models: SessionFilters, QuickMatchRequest, LeaveSessionRequest
- Response models: ParticipantInfo, SessionInfo, QuickMatchResponse, UpcomingSession,
                   TimeSlotInfo, UpcomingSlotsResponse
- Database models: SessionDB, ParticipantDB
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import MAX_PARTICIPANTS, REASON_TEXT_MAX_LENGTH, TOPIC_MAX_LENGTH


class TableMode(str, Enum):
    """Table audio mode."""

    FORCED_AUDIO = "forced_audio"  # Mic required ON
    QUIET = "quiet"  # Muted by default, text chat primary


class SessionPhase(str, Enum):
    """Session phase in the 55-minute structure."""

    SETUP = "setup"  # 0-3 min: trickle-in
    WORK_1 = "work_1"  # 3-28 min: first work block (25 min)
    BREAK = "break"  # 28-30 min: rest (2 min)
    WORK_2 = "work_2"  # 30-50 min: second work block (20 min)
    SOCIAL = "social"  # 50-55 min: chat/rating (5 min)
    ENDED = "ended"  # Session complete


class ParticipantType(str, Enum):
    """Type of session participant."""

    HUMAN = "human"
    AI_COMPANION = "ai_companion"


# --- Request Models ---


class SessionFilters(BaseModel):
    """Filters for quick-match session finding."""

    topic: Optional[str] = Field(None, max_length=TOPIC_MAX_LENGTH)
    mode: Optional[TableMode] = None
    language: Optional[str] = None  # "en" or "zh-TW"

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in ("en", "zh-TW"):
            raise ValueError("Language must be 'en' or 'zh-TW'")
        return v


class QuickMatchRequest(BaseModel):
    """Request to quick-match into a session."""

    filters: Optional[SessionFilters] = None
    target_slot_time: Optional[datetime] = Field(
        None, description="Specific :00/:30 slot to join (if omitted, uses next available)"
    )


class LeaveSessionRequest(BaseModel):
    """Request to leave a session early."""

    reason: Optional[str] = Field(None, max_length=REASON_TEXT_MAX_LENGTH)


# --- Response Models ---


class ParticipantInfo(BaseModel):
    """Information about a session participant."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None  # None for AI companions
    participant_type: ParticipantType
    seat_number: int = Field(..., ge=1, le=MAX_PARTICIPANTS)
    username: Optional[str] = None
    display_name: Optional[str] = None
    avatar_config: dict[str, Any] = Field(default_factory=dict)
    pixel_avatar_id: Optional[str] = None
    joined_at: datetime
    is_active: bool = True  # False if left_at is set

    # AI companion specific
    ai_companion_name: Optional[str] = None


class SessionInfo(BaseModel):
    """Full session details response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    start_time: datetime
    end_time: datetime
    mode: TableMode
    topic: Optional[str] = None
    language: str = "en"
    current_phase: SessionPhase
    phase_started_at: Optional[datetime] = None
    room_type: Optional[str] = None
    participants: list[ParticipantInfo] = Field(default_factory=list)
    available_seats: int = Field(..., ge=0, le=MAX_PARTICIPANTS)
    livekit_room_name: str


class QuickMatchResponse(BaseModel):
    """Response from quick-match endpoint."""

    session: SessionInfo
    livekit_token: str
    seat_number: int = Field(..., ge=1, le=MAX_PARTICIPANTS)
    credit_deducted: bool = True
    wait_minutes: int = Field(..., description="Minutes until session starts (0 if immediate)")
    is_immediate: bool = Field(..., description="True if session starts within 1 minute")


class UpcomingSession(BaseModel):
    """Simplified session info for listings."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    start_time: datetime
    end_time: datetime
    mode: TableMode
    topic: Optional[str] = None
    language: str = "en"
    current_phase: SessionPhase
    participant_count: int = Field(..., ge=0, le=MAX_PARTICIPANTS)
    my_seat_number: int = Field(..., ge=1, le=MAX_PARTICIPANTS)


class UpcomingSessionsResponse(BaseModel):
    """Response for upcoming sessions list."""

    sessions: list[UpcomingSession] = Field(default_factory=list)


class TimeSlotInfo(BaseModel):
    """Information about an upcoming time slot for the Find Table hero."""

    start_time: datetime
    queue_count: int = Field(0, ge=0, description="Actual human signups for this slot")
    estimated_count: int = Field(0, ge=0, description="Historical estimate for this time of day")
    has_user_session: bool = Field(False, description="True if user already joined this slot")


class UpcomingSlotsResponse(BaseModel):
    """Response for upcoming time slots endpoint."""

    slots: list[TimeSlotInfo] = Field(default_factory=list)


class LeaveSessionResponse(BaseModel):
    """Response from leave session endpoint."""

    status: str = "left"
    session_id: str


class CancelSessionResponse(BaseModel):
    """Response from cancel session endpoint."""

    status: str = "cancelled"
    session_id: str
    credit_refunded: bool
    message: str


# --- Database Row Models ---


class SessionDB(BaseModel):
    """Database row model for sessions table."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    start_time: datetime
    end_time: datetime
    mode: str  # Store as string, convert to enum in service
    topic: Optional[str] = None
    language: str = "en"
    current_phase: str  # Store as string, convert to enum in service
    phase_started_at: Optional[datetime] = None
    room_type: Optional[str] = None
    livekit_room_name: str
    created_at: datetime
    updated_at: datetime


class ParticipantDB(BaseModel):
    """Database row model for session_participants table."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    user_id: Optional[str] = None  # None for AI companions
    participant_type: str  # 'human' or 'ai_companion'
    seat_number: int
    ai_companion_name: Optional[str] = None
    ai_companion_avatar: Optional[dict[str, Any]] = None
    joined_at: datetime
    left_at: Optional[datetime] = None
    disconnect_count: int = 0
    total_active_minutes: int = 0
    essence_earned: bool = False


# --- Internal Models ---


class SessionCreate(BaseModel):
    """Internal model for creating a new session."""

    start_time: datetime
    end_time: datetime
    mode: TableMode
    topic: Optional[str] = None
    language: str = "en"
    livekit_room_name: str


class ParticipantCreate(BaseModel):
    """Internal model for adding a participant."""

    session_id: str
    user_id: Optional[str] = None
    participant_type: ParticipantType
    seat_number: int = Field(..., ge=1, le=MAX_PARTICIPANTS)
    ai_companion_name: Optional[str] = None
    ai_companion_avatar: Optional[dict[str, Any]] = None


class SessionSummaryResponse(BaseModel):
    """Response for session summary endpoint."""

    focus_minutes: int = Field(..., ge=0)
    essence_earned: bool = False
    tablemate_count: int = Field(..., ge=0)
    phases_completed: int = Field(..., ge=0, le=5)
    total_phases: int = 5
    mode: TableMode
    topic: Optional[str] = None
