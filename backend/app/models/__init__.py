"""Pydantic models for Focus Squad API."""

from app.models.credit import (
    TIER_CONFIG,
    ApplyReferralRequest,
    ApplyReferralResponse,
    CreditBalance,
    CreditBalanceDB,
    CreditNotFoundError,
    CreditServiceError,
    CreditTransaction,
    GiftLimitExceededError,
    GiftNotAllowedError,
    GiftRequest,
    GiftResponse,
    InsufficientCreditsError,
    InvalidReferralCodeError,
    ReferralAlreadyAppliedError,
    ReferralInfo,
    SelfReferralError,
    TransactionType,
    UserTier,
)
from app.models.user import UserProfile, UserProfileUpdate, UserPublicProfile

__all__ = [
    # User models
    "UserProfile",
    "UserProfileUpdate",
    "UserPublicProfile",
    # Credit models
    "ApplyReferralRequest",
    "ApplyReferralResponse",
    "CreditBalance",
    "CreditBalanceDB",
    "CreditNotFoundError",
    "CreditServiceError",
    "CreditTransaction",
    "GiftLimitExceededError",
    "GiftNotAllowedError",
    "GiftRequest",
    "GiftResponse",
    "InsufficientCreditsError",
    "InvalidReferralCodeError",
    "ReferralAlreadyAppliedError",
    "ReferralInfo",
    "SelfReferralError",
    "TIER_CONFIG",
    "TransactionType",
    "UserTier",
]
