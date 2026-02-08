"""
Peer review / rating models.

Aligned with design doc: output/plan/2026-02-08-peer-review-system.md
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# ===========================================
# Enums
# ===========================================


class RatingValue(str, Enum):
    """Rating options for peer review."""

    GREEN = "green"
    RED = "red"
    SKIP = "skip"


class RedRatingReason(str, Enum):
    """Structured reasons for a Red rating."""

    ABSENT = "absent_no_show"
    DISRUPTIVE = "disruptive_behavior"
    LEFT_EARLY = "left_early_no_notice"
    NOT_WORKING = "not_actually_working"
    OTHER = "other"


class ReliabilityTier(str, Enum):
    """Display tiers for reliability badge."""

    TRUSTED = "trusted"  # 95-100
    GOOD = "good"  # 80-94
    FAIR = "fair"  # 60-79
    NEW = "new"  # <5 non-skip ratings received


# ===========================================
# Request Models
# ===========================================


class SingleRating(BaseModel):
    """One rating for one tablemate."""

    ratee_id: str
    rating: RatingValue
    reasons: Optional[list[RedRatingReason]] = None
    other_reason_text: Optional[str] = Field(None, max_length=500)


class SubmitRatingsRequest(BaseModel):
    """Batch submission: all ratings for a session at once."""

    ratings: list[SingleRating] = Field(..., min_length=1, max_length=3)


# ===========================================
# Response Models
# ===========================================


class RatingSubmitResponse(BaseModel):
    """Response after submitting ratings."""

    success: bool = True
    ratings_submitted: int
    message: str = "Ratings submitted successfully"


class RateableUser(BaseModel):
    """A tablemate available for rating."""

    user_id: str
    username: str
    display_name: Optional[str] = None
    avatar_config: dict = Field(default_factory=dict)


class PendingRatingInfo(BaseModel):
    """Info about a pending rating the user needs to complete."""

    session_id: str
    rateable_users: list[RateableUser]
    expires_at: datetime


class PendingRatingsResponse(BaseModel):
    """Response for pending ratings check."""

    has_pending: bool
    pending: Optional[PendingRatingInfo] = None


class ReliabilityInfo(BaseModel):
    """User's reliability score and tier for display."""

    model_config = ConfigDict(from_attributes=True)

    score: Decimal
    tier: ReliabilityTier
    total_ratings_received: int
    is_new_user: bool


# ===========================================
# Internal / DB Models
# ===========================================


class RatingRecord(BaseModel):
    """A rating record from the database."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    rater_id: str
    ratee_id: str
    rating: RatingValue
    rater_reliability_at_time: Optional[Decimal] = None
    weight: Decimal = Decimal("1.0")
    reason: Optional[dict] = None
    created_at: datetime


# ===========================================
# Exception Classes
# ===========================================


class RatingServiceError(Exception):
    """Base exception for rating service errors."""

    pass


class RatingAlreadyExistsError(RatingServiceError):
    """User already rated this person for this session."""

    pass


class InvalidRatingTargetError(RatingServiceError):
    """Target user was not a human participant in this session."""

    pass


class SessionNotRatableError(RatingServiceError):
    """Session is not in a ratable state (not ended/social)."""

    pass


class NoPendingRatingsError(RatingServiceError):
    """No pending ratings found for this session."""

    pass


class RedReasonRequiredError(RatingServiceError):
    """Red rating submitted without required reasons."""

    pass
