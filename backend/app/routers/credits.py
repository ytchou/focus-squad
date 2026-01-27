from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

router = APIRouter()


class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ELITE = "elite"
    INFINITE = "infinite"


# Weekly credit allowances by tier
TIER_CREDITS = {
    UserTier.FREE: 2,
    UserTier.PRO: 8,
    UserTier.ELITE: 12,
    UserTier.INFINITE: float("inf"),
}


class CreditBalance(BaseModel):
    """User's credit balance information."""
    tier: UserTier
    credits_remaining: int
    credits_used_this_week: int
    weekly_allowance: int
    next_refresh: datetime
    gifts_sent_this_week: int
    max_gifts_per_week: int


class GiftCreditsRequest(BaseModel):
    """Request to gift credits to another user."""
    recipient_id: str
    amount: int = 1


class ReferralInfo(BaseModel):
    """Referral program information."""
    referral_code: str
    referrals_completed: int
    credits_earned_from_referrals: int


@router.get("/balance", response_model=CreditBalance)
async def get_credit_balance():
    """Get current user's credit balance."""
    # TODO: Implement with auth
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/gift")
async def gift_credits(request: GiftCreditsRequest):
    """Gift credits to another user (Pro/Elite only)."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/referral", response_model=ReferralInfo)
async def get_referral_info():
    """Get current user's referral code and stats."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/referral/apply")
async def apply_referral_code(code: str):
    """Apply a referral code (for new users)."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")
