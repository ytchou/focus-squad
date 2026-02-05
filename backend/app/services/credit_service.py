"""
Credit service for balance and transaction operations.

Handles:
- Credit balance queries
- Credit deduction for session joining
- Transaction logging

Full credit features (gifting, referrals, weekly refresh) to be added later.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict
from supabase import Client

from app.core.database import get_supabase


class UserTier(str, Enum):
    """User subscription tier."""

    FREE = "free"
    PRO = "pro"
    ELITE = "elite"
    INFINITE = "infinite"


class TransactionType(str, Enum):
    """Credit transaction types."""

    SESSION_JOIN = "session_join"
    GIFT_SENT = "gift_sent"
    GIFT_RECEIVED = "gift_received"
    REFERRAL = "referral"
    WEEKLY_REFRESH = "weekly_refresh"
    PENALTY = "penalty"


class CreditBalance(BaseModel):
    """Credit balance response model."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    tier: UserTier
    credits_remaining: int
    credits_used_this_week: int
    week_start_date: Optional[datetime] = None


class CreditTransaction(BaseModel):
    """Credit transaction record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    amount: int  # positive = earned, negative = spent
    transaction_type: str
    description: Optional[str] = None
    related_user_id: Optional[str] = None
    created_at: datetime


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
            f"Insufficient credits for user {user_id}: "
            f"required {required}, available {available}"
        )


class CreditNotFoundError(CreditServiceError):
    """Credit record not found for user."""

    pass


class CreditService:
    """Service for credit balance and transaction operations."""

    # Weekly credit limits by tier
    TIER_WEEKLY_LIMITS = {
        UserTier.FREE: 2,
        UserTier.PRO: 8,
        UserTier.ELITE: 12,
        UserTier.INFINITE: 999999,  # Effectively unlimited
    }

    def __init__(self, supabase: Optional[Client] = None):
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    def get_balance(self, user_id: str) -> CreditBalance:
        """
        Get credit balance for a user.

        Args:
            user_id: Internal user UUID

        Returns:
            CreditBalance with tier and credits_remaining

        Raises:
            CreditNotFoundError: If no credit record exists for user
        """
        result = (
            self.supabase.table("credits")
            .select("user_id, tier, credits_remaining, credits_used_this_week, week_start_date")
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data:
            raise CreditNotFoundError(f"No credit record found for user {user_id}")

        return CreditBalance(**result.data[0])

    def has_sufficient_credits(self, user_id: str, amount: int = 1) -> bool:
        """
        Check if user has sufficient credits.

        Args:
            user_id: Internal user UUID
            amount: Credits required (default 1)

        Returns:
            True if user has enough credits
        """
        try:
            balance = self.get_balance(user_id)
            return balance.credits_remaining >= amount
        except CreditNotFoundError:
            return False

    def deduct_credit(
        self,
        user_id: str,
        amount: int,
        transaction_type: TransactionType,
        description: Optional[str] = None,
        related_user_id: Optional[str] = None,
    ) -> CreditTransaction:
        """
        Deduct credits from user balance and log transaction.

        Args:
            user_id: Internal user UUID
            amount: Credits to deduct (positive number)
            transaction_type: Type of transaction
            description: Optional description
            related_user_id: Optional related user (for gifts)

        Returns:
            CreditTransaction record

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
            CreditNotFoundError: If no credit record exists
        """
        # Get current balance
        balance = self.get_balance(user_id)

        if balance.credits_remaining < amount:
            raise InsufficientCreditsError(
                user_id=user_id,
                required=amount,
                available=balance.credits_remaining,
            )

        # Update balance (decrement credits_remaining, increment credits_used_this_week)
        new_remaining = balance.credits_remaining - amount
        new_used = balance.credits_used_this_week + amount

        self.supabase.table("credits").update(
            {
                "credits_remaining": new_remaining,
                "credits_used_this_week": new_used,
            }
        ).eq("user_id", user_id).execute()

        # Log transaction (negative amount for deduction)
        transaction_data = {
            "user_id": user_id,
            "amount": -amount,  # Negative for spending
            "transaction_type": transaction_type.value,
            "description": description,
            "related_user_id": related_user_id,
        }

        result = (
            self.supabase.table("credit_transactions")
            .insert(transaction_data)
            .execute()
        )

        if not result.data:
            raise CreditServiceError("Failed to create transaction record")

        return CreditTransaction(**result.data[0])

    def add_credit(
        self,
        user_id: str,
        amount: int,
        transaction_type: TransactionType,
        description: Optional[str] = None,
        related_user_id: Optional[str] = None,
    ) -> CreditTransaction:
        """
        Add credits to user balance and log transaction.

        Args:
            user_id: Internal user UUID
            amount: Credits to add (positive number)
            transaction_type: Type of transaction
            description: Optional description
            related_user_id: Optional related user (for gifts/referrals)

        Returns:
            CreditTransaction record
        """
        # Get current balance
        balance = self.get_balance(user_id)

        # Update balance (increment credits_remaining)
        new_remaining = balance.credits_remaining + amount

        self.supabase.table("credits").update(
            {"credits_remaining": new_remaining}
        ).eq("user_id", user_id).execute()

        # Log transaction (positive amount for earning)
        transaction_data = {
            "user_id": user_id,
            "amount": amount,  # Positive for earning
            "transaction_type": transaction_type.value,
            "description": description,
            "related_user_id": related_user_id,
        }

        result = (
            self.supabase.table("credit_transactions")
            .insert(transaction_data)
            .execute()
        )

        if not result.data:
            raise CreditServiceError("Failed to create transaction record")

        return CreditTransaction(**result.data[0])
