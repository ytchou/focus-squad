"""
Credit system models.

Consolidated from credit_service.py and routers/credits.py.
Aligned with design doc: output/plan/2025-02-06-credit-system-redesign.md
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import REFERRAL_CODE_MAX_LENGTH


class UserTier(str, Enum):
    """User subscription tier."""

    FREE = "free"
    PRO = "pro"
    ELITE = "elite"
    INFINITE = "infinite"
    ADMIN = "admin"  # Not purchasable, set via database only. Grants debug access.


class TransactionType(str, Enum):
    """Credit transaction types."""

    SESSION_JOIN = "session_join"
    GIFT_SENT = "gift_sent"
    GIFT_RECEIVED = "gift_received"
    REFERRAL = "referral"
    WEEKLY_REFRESH = "weekly_refresh"
    PENALTY = "penalty"
    REFUND = "refund"  # New: for session cancellation refunds


# Tier configuration: limits and capabilities
TIER_CONFIG = {
    UserTier.FREE: {"weekly": 2, "max": 4, "can_gift": False, "gift_limit": 0},
    UserTier.PRO: {"weekly": 8, "max": 16, "can_gift": True, "gift_limit": 4},
    UserTier.ELITE: {"weekly": 12, "max": 24, "can_gift": True, "gift_limit": 4},
    UserTier.INFINITE: {"weekly": 999999, "max": 999999, "can_gift": False, "gift_limit": 0},
    UserTier.ADMIN: {"weekly": 999999, "max": 999999, "can_gift": True, "gift_limit": 999},
}


class CreditBalance(BaseModel):
    """User's current credit state (API response model)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    tier: UserTier
    credits_remaining: int
    weekly_allowance: int = Field(description="Tier's weekly credit limit")
    max_balance: int = Field(description="Maximum balance (2x tier limit)")
    gifts_sent_this_week: int = 0
    max_gifts_per_week: int = Field(description="0 for Free/Infinite, 4 for Pro/Elite")
    credit_cycle_start: date = Field(description="Start of rolling 7-day cycle")
    next_refresh: datetime = Field(description="When credits will refresh (cycle_start + 7 days)")
    referral_code: Optional[str] = None


class CreditBalanceDB(BaseModel):
    """Credit record from database (internal model)."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    tier: UserTier
    credits_remaining: int
    gifts_sent_this_week: int = 0
    credit_cycle_start: Optional[date] = None
    referral_code: Optional[str] = None
    referred_by: Optional[str] = None
    referrals_completed: int = 0


class CreditTransaction(BaseModel):
    """Credit transaction record (audit log)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    amount: int  # positive = earned, negative = spent
    transaction_type: str
    description: Optional[str] = None
    related_user_id: Optional[str] = None
    created_at: datetime


# Request models


class GiftRequest(BaseModel):
    """Request to gift credits to another user."""

    recipient_user_id: str
    amount: int = Field(default=1, ge=1, le=4, description="Credits to gift (1-4)")


class ApplyReferralRequest(BaseModel):
    """Request to apply a referral code."""

    referral_code: str = Field(min_length=1, max_length=REFERRAL_CODE_MAX_LENGTH)


# Response models


class GiftResponse(BaseModel):
    """Response after gifting credits."""

    success: bool
    new_balance: int
    message: str = "Credits gifted successfully"


class ReferralInfo(BaseModel):
    """Referral program information."""

    referral_code: str
    referrals_completed: int
    referred_by: Optional[str] = Field(default=None, description="Username of referrer (if any)")
    shareable_link: str = Field(description="Full URL to share")


class ApplyReferralResponse(BaseModel):
    """Response after applying a referral code."""

    success: bool
    referred_by_username: str
    message: str = (
        "Referral code applied. You'll both earn a bonus credit after your first session!"
    )


# Exception classes


class CreditServiceError(Exception):
    """Base exception for credit service errors."""

    pass


class InsufficientCreditsError(CreditServiceError):
    """User does not have enough credits."""

    def __init__(self, user_id: str, required: int, available: int):
        self.user_id = user_id
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient credits for user {user_id}: required {required}, available {available}"
        )


class CreditNotFoundError(CreditServiceError):
    """Credit record not found for user."""

    pass


class GiftNotAllowedError(CreditServiceError):
    """User's tier does not allow gifting."""

    def __init__(self, tier: UserTier):
        self.tier = tier
        super().__init__(f"Gifting not allowed for tier: {tier.value}")


class GiftLimitExceededError(CreditServiceError):
    """User has exceeded weekly gift limit."""

    def __init__(self, sent: int, limit: int):
        self.sent = sent
        self.limit = limit
        super().__init__(f"Weekly gift limit exceeded: {sent}/{limit}")


class ReferralAlreadyAppliedError(CreditServiceError):
    """User has already applied a referral code."""

    pass


class InvalidReferralCodeError(CreditServiceError):
    """Referral code does not exist."""

    pass


class SelfReferralError(CreditServiceError):
    """User tried to use their own referral code."""

    pass
