"""
Gamification models for Phase 4B: Diary Integration.

Covers:
- Weekly streak bonuses
- Companion mood and reactions
- Growth timeline snapshots
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Streak Models
# =============================================================================


class WeeklyStreakResponse(BaseModel):
    """Current week's session streak status."""

    session_count: int = 0
    week_start: date
    next_bonus_at: int = 3
    bonus_3_awarded: bool = False
    bonus_5_awarded: bool = False
    total_bonus_earned: int = 0


class StreakBonusResult(BaseModel):
    """Returned when a streak bonus is awarded."""

    bonus_essence: int
    threshold_reached: int
    new_balance: int


# =============================================================================
# Mood & Reaction Models
# =============================================================================


class MoodResponse(BaseModel):
    """Companion mood baseline computed from recent diary tags."""

    mood: str  # "positive" | "neutral" | "tired"
    score: float
    positive_count: int
    negative_count: int
    total_count: int


class CompanionReactionResponse(BaseModel):
    """Companion reaction animation triggered by a diary tag."""

    companion_type: str
    animation: str  # CSS animation name from DIARY_TAG_REACTIONS
    tag: str


class DiaryNoteWithReactionResponse(BaseModel):
    """Extended diary note response including companion reaction data."""

    session_id: str
    note: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    companion_reaction: Optional[CompanionReactionResponse] = None
    mood: Optional[MoodResponse] = None


# =============================================================================
# Timeline Models
# =============================================================================


class RoomSnapshot(BaseModel):
    """A milestone snapshot in the growth timeline."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    milestone_type: str
    image_url: str
    session_count_at: int = 0
    diary_excerpt: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class TimelineResponse(BaseModel):
    """Paginated timeline of room snapshots."""

    snapshots: list[RoomSnapshot]
    total: int
    page: int
    per_page: int


class SnapshotUploadRequest(BaseModel):
    """Upload a room snapshot for a milestone event."""

    milestone_type: str
    image_base64: str
    diary_excerpt: Optional[str] = Field(None, max_length=200)
    metadata: dict = Field(default_factory=dict)


class SnapshotUploadResponse(BaseModel):
    """Response after uploading a snapshot."""

    id: str
    image_url: str
    milestone_type: str
    created_at: datetime


# =============================================================================
# Exceptions
# =============================================================================


class StreakServiceError(Exception):
    """Base exception for streak service errors."""

    pass


class TimelineServiceError(Exception):
    """Base exception for timeline service errors."""

    pass


class InvalidMilestoneTypeError(TimelineServiceError):
    """Invalid milestone type provided."""

    pass


class SnapshotTooLargeError(TimelineServiceError):
    """Snapshot image exceeds size limit."""

    pass


class MoodServiceError(Exception):
    """Base exception for mood service errors."""

    pass
