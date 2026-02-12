"""
Accountability partner models.

Aligned with design doc: output/plan/2026-02-12-accountability-partners-design.md
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    INTEREST_TAGS,
    MAX_INTEREST_TAGS_PER_USER,
    MAX_PRIVATE_TABLE_SEATS,
    MIN_PRIVATE_TABLE_SEATS,
    TOPIC_MAX_LENGTH,
)

# ===========================================
# Enums
# ===========================================


class PartnershipStatus(str, Enum):
    """Status of a partnership request."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class InvitationStatus(str, Enum):
    """Status of a table invitation."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


# ===========================================
# Request Models
# ===========================================


class PartnerRequestCreate(BaseModel):
    """Send a partnership request to another user."""

    addressee_id: str


class PartnerRequestRespond(BaseModel):
    """Accept or decline a partnership request."""

    accept: bool


class InvitationRespond(BaseModel):
    """Accept or decline a table invitation."""

    accept: bool


class CreatePrivateTableRequest(BaseModel):
    """Create a private table and invite partners."""

    partner_ids: list[str] = Field(..., min_length=1, max_length=3)
    time_slot: datetime
    mode: str = "forced_audio"
    max_seats: int = Field(
        MAX_PRIVATE_TABLE_SEATS,
        ge=MIN_PRIVATE_TABLE_SEATS,
        le=MAX_PRIVATE_TABLE_SEATS,
    )
    fill_ai: bool = True
    topic: Optional[str] = Field(None, max_length=TOPIC_MAX_LENGTH)


class UpdateInterestTagsRequest(BaseModel):
    """Set interest tags on user profile."""

    tags: list[str] = Field(..., max_length=MAX_INTEREST_TAGS_PER_USER)

    @classmethod
    def validate_tags(cls, tags: list[str]) -> list[str]:
        invalid = [t for t in tags if t not in INTEREST_TAGS]
        if invalid:
            raise ValueError(f"Invalid tags: {invalid}. Valid tags: {INTEREST_TAGS}")
        return tags


# ===========================================
# Response Models
# ===========================================


class PartnerInfo(BaseModel):
    """A partner in the user's partner list."""

    model_config = ConfigDict(from_attributes=True)

    partnership_id: str
    user_id: str
    username: str
    display_name: Optional[str] = None
    avatar_config: dict[str, Any] = Field(default_factory=dict)
    pixel_avatar_id: Optional[str] = None
    study_interests: list[str] = Field(default_factory=list)
    reliability_score: Decimal = Decimal("100.00")
    last_session_together: Optional[datetime] = None


class PartnerListResponse(BaseModel):
    """Response for listing partners."""

    partners: list[PartnerInfo]
    total: int


class PartnerRequestInfo(BaseModel):
    """A pending partnership request."""

    partnership_id: str
    user_id: str
    username: str
    display_name: Optional[str] = None
    avatar_config: dict[str, Any] = Field(default_factory=dict)
    pixel_avatar_id: Optional[str] = None
    direction: str  # "incoming" or "outgoing"
    created_at: datetime


class PartnerRequestsResponse(BaseModel):
    """Response for listing pending requests."""

    requests: list[PartnerRequestInfo]


class InvitationInfo(BaseModel):
    """A pending table invitation."""

    id: str
    session_id: str
    inviter_id: str
    inviter_name: str
    time_slot: datetime
    mode: str
    topic: Optional[str] = None
    status: InvitationStatus
    created_at: datetime


class PendingInvitationsResponse(BaseModel):
    """Response for listing pending invitations."""

    invitations: list[InvitationInfo]


class CreatePrivateTableResponse(BaseModel):
    """Response from creating a private table."""

    session_id: str
    invitations_sent: int
    credit_deducted: bool = True


class UserSearchResult(BaseModel):
    """A user from search results."""

    user_id: str
    username: str
    display_name: Optional[str] = None
    avatar_config: dict[str, Any] = Field(default_factory=dict)
    pixel_avatar_id: Optional[str] = None
    study_interests: list[str] = Field(default_factory=list)
    partnership_status: Optional[str] = None  # None, "pending", "accepted"


class UserSearchResponse(BaseModel):
    """Response for user search."""

    users: list[UserSearchResult]


class PartnerRequestResponse(BaseModel):
    """Response after sending a partner request."""

    partnership_id: str
    status: str = "pending"
    message: str = "Partner request sent"


class PartnerRespondResponse(BaseModel):
    """Response after responding to a partner request."""

    partnership_id: str
    status: str
    message: str


class PartnerRemoveResponse(BaseModel):
    """Response after removing a partner."""

    message: str = "Partner removed"


# ===========================================
# Exception Classes
# ===========================================


class PartnerServiceError(Exception):
    """Base exception for partner service errors."""

    pass


class PartnershipNotFoundError(PartnerServiceError):
    """Partnership not found."""

    pass


class AlreadyPartnersError(PartnerServiceError):
    """Users are already partners or have a pending request."""

    pass


class PartnerRequestExistsError(PartnerServiceError):
    """A partner request already exists between these users."""

    pass


class SelfPartnerError(PartnerServiceError):
    """Cannot send partner request to yourself."""

    pass


class PartnerLimitError(PartnerServiceError):
    """Maximum number of partners reached."""

    pass


class InvitationNotFoundError(PartnerServiceError):
    """Table invitation not found."""

    pass


class InvitationExpiredError(PartnerServiceError):
    """Table invitation has expired."""

    pass


class NotPartnerError(PartnerServiceError):
    """User is not a partner (cannot invite to private table)."""

    pass


class InvalidInterestTagError(PartnerServiceError):
    """One or more interest tags are not valid."""

    pass
