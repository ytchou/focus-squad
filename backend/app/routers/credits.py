"""
Credit system API endpoints.

Handles:
- GET /balance - Get user's credit state
- POST /gift - Gift credits to another user
- GET /referral - Get referral code and stats
- POST /referral/apply - Apply a referral code
- POST /notify-interest - Register upgrade pricing interest
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.core.auth import AuthUser, require_auth_from_state
from app.core.database import get_supabase
from app.core.rate_limit import limiter
from app.models.credit import (
    ApplyReferralRequest,
    ApplyReferralResponse,
    CreditBalance,
    GiftRequest,
    GiftResponse,
    NotifyInterestResponse,
    ReferralInfo,
)
from app.core.posthog import capture as posthog_capture
from app.services.credit_service import CreditService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

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

    return credit_service.get_balance(profile.id)


@router.post("/gift", response_model=GiftResponse)
@limiter.limit("10/minute")
async def gift_credits(
    request: Request,
    gift_request: GiftRequest,
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

    posthog_capture(
        user_id=str(profile.id),
        event="credit_gifted",
        properties={
            "recipient_user_id": str(gift_request.recipient_user_id),
            "amount": gift_request.amount,
        },
    )

    return credit_service.gift_credit(
        sender_id=profile.id,
        recipient_id=gift_request.recipient_user_id,
        amount=gift_request.amount,
        idempotency_key=x_idempotency_key,
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

    return credit_service.get_referral_info(profile.id)


@router.post("/referral/apply", response_model=ApplyReferralResponse)
@limiter.limit("5/minute")
async def apply_referral_code(
    request: Request,
    referral_request: ApplyReferralRequest,
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

    referrer_username = credit_service.apply_referral_code(
        user_id=profile.id,
        referral_code=referral_request.referral_code,
    )
    return ApplyReferralResponse(
        success=True,
        referred_by_username=referrer_username,
    )


@router.post("/notify-interest", response_model=NotifyInterestResponse)
@limiter.limit("5/minute")
async def register_upgrade_interest(
    request: Request,
    user: AuthUser = Depends(require_auth_from_state),
    user_service: UserService = Depends(get_user_service),
) -> NotifyInterestResponse:
    """
    Register user's interest in paid tier upgrades.

    Idempotent: duplicate calls are silently ignored.
    Uses the user's existing email from their profile.
    """
    profile = user_service.get_user_by_auth_id(user.auth_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        supabase = get_supabase()
        supabase.table("upgrade_interest").upsert(
            {"user_id": profile.id, "email": profile.email},
            on_conflict="user_id",
        ).execute()
    except Exception:
        logger.exception("Failed to register upgrade interest for user %s", profile.id)
        raise HTTPException(status_code=500, detail="Failed to register interest")

    logger.info("Upgrade interest registered for user %s", profile.id)
    return NotifyInterestResponse(success=True)
