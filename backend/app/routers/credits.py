"""
Credit system API endpoints.

Handles:
- GET /balance - Get user's credit state
- POST /gift - Gift credits to another user
- GET /referral - Get referral code and stats
- POST /referral/apply - Apply a referral code
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.auth import AuthUser, require_auth_from_state
from app.models.credit import (
    ApplyReferralRequest,
    ApplyReferralResponse,
    CreditBalance,
    CreditNotFoundError,
    GiftLimitExceededError,
    GiftNotAllowedError,
    GiftRequest,
    GiftResponse,
    InsufficientCreditsError,
    InvalidReferralCodeError,
    ReferralAlreadyAppliedError,
    ReferralInfo,
    SelfReferralError,
)
from app.services.credit_service import CreditService
from app.services.user_service import UserService

router = APIRouter()


def get_credit_service() -> CreditService:
    """Dependency to get CreditService instance."""
    return CreditService()


def get_user_service() -> UserService:
    """Dependency to get UserService instance."""
    return UserService()


@router.get("/balance", response_model=CreditBalance)
async def get_credit_balance(
    user: AuthUser = Depends(require_auth_from_state),
    credit_service: CreditService = Depends(get_credit_service),
    user_service: UserService = Depends(get_user_service),
) -> CreditBalance:
    """
    Get current user's credit balance.

    Returns tier, credits remaining, weekly allowance, gift limits,
    and next refresh date.
    """
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        return credit_service.get_balance(profile.id)
    except CreditNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit record not found. Please complete onboarding.",
        )


@router.post("/gift", response_model=GiftResponse)
async def gift_credits(
    request: GiftRequest,
    user: AuthUser = Depends(require_auth_from_state),
    credit_service: CreditService = Depends(get_credit_service),
    user_service: UserService = Depends(get_user_service),
    x_idempotency_key: Optional[str] = Header(None),
) -> GiftResponse:
    """
    Gift credits to another user.

    Only Pro and Elite tier users can gift credits.
    Weekly limit: 4 credits per week.
    Accepts optional X-Idempotency-Key header to prevent duplicate processing.
    """
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        return credit_service.gift_credit(
            sender_id=profile.id,
            recipient_id=request.recipient_user_id,
            amount=request.amount,
            idempotency_key=x_idempotency_key,
        )
    except GiftNotAllowedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Gifting not allowed for {e.tier.value} tier. Upgrade to Pro or Elite.",
        )
    except GiftLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Weekly gift limit reached ({e.sent}/{e.limit}). Resets on your refresh date.",
        )
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Available: {e.available}, Required: {e.required}",
        )
    except CreditNotFoundError as e:
        if "Recipient" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipient user not found.",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit record not found.",
        )


@router.get("/referral", response_model=ReferralInfo)
async def get_referral_info(
    user: AuthUser = Depends(require_auth_from_state),
    credit_service: CreditService = Depends(get_credit_service),
    user_service: UserService = Depends(get_user_service),
) -> ReferralInfo:
    """
    Get current user's referral code and stats.

    Returns the shareable referral link and count of successful referrals.
    """
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        return credit_service.get_referral_info(profile.id)
    except CreditNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit record not found.",
        )


@router.post("/referral/apply", response_model=ApplyReferralResponse)
async def apply_referral_code(
    request: ApplyReferralRequest,
    user: AuthUser = Depends(require_auth_from_state),
    credit_service: CreditService = Depends(get_credit_service),
    user_service: UserService = Depends(get_user_service),
) -> ApplyReferralResponse:
    """
    Apply a referral code.

    Can only be done once per user. Both parties earn +1 credit
    when the new user completes their first session.
    """
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        referrer_username = credit_service.apply_referral_code(
            user_id=profile.id,
            referral_code=request.referral_code,
        )
        return ApplyReferralResponse(
            success=True,
            referred_by_username=referrer_username,
        )
    except ReferralAlreadyAppliedError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already used a referral code.",
        )
    except SelfReferralError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot use your own referral code.",
        )
    except InvalidReferralCodeError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid referral code.",
        )
    except CreditNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit record not found.",
        )
