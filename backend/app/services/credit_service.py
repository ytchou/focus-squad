"""
Credit service for balance and transaction operations.

Handles:
- Credit balance queries
- Credit deduction for session joining
- Credit refunds for session cancellation
- Credit gifting between users
- Referral code management
- Rolling 7-day credit refresh

Design doc: output/plan/2025-02-06-credit-system-redesign.md
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from supabase import Client

from app.core.database import get_supabase
from app.models.credit import (
    TIER_CONFIG,
    CreditBalance,
    CreditBalanceDB,
    CreditNotFoundError,
    CreditServiceError,
    CreditTransaction,
    GiftLimitExceededError,
    GiftNotAllowedError,
    GiftResponse,
    InsufficientCreditsError,
    InvalidReferralCodeError,
    ReferralAlreadyAppliedError,
    ReferralInfo,
    SelfReferralError,
    TransactionType,
)


class CreditService:
    """Service for credit balance and transaction operations."""

    def __init__(self, supabase: Optional[Client] = None):
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    def _get_db_record(self, user_id: str) -> CreditBalanceDB:
        """Get raw credit record from database."""
        result = (
            self.supabase.table("credits")
            .select(
                "user_id, tier, credits_remaining, gifts_sent_this_week, "
                "credit_cycle_start, referral_code, referred_by, referrals_completed"
            )
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data:
            raise CreditNotFoundError(f"No credit record found for user {user_id}")

        return CreditBalanceDB(**result.data[0])

    def get_balance(self, user_id: str) -> CreditBalance:
        """
        Get credit balance for a user with computed fields.

        Args:
            user_id: Internal user UUID

        Returns:
            CreditBalance with tier, credits_remaining, and computed fields

        Raises:
            CreditNotFoundError: If no credit record exists for user
        """
        db_record = self._get_db_record(user_id)
        tier_config = TIER_CONFIG[db_record.tier]

        # Compute next refresh date (cycle_start + 7 days at 00:00 UTC)
        cycle_start = db_record.credit_cycle_start or datetime.now(timezone.utc).date()
        next_refresh = datetime.combine(
            cycle_start + timedelta(days=7),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )

        return CreditBalance(
            user_id=db_record.user_id,
            tier=db_record.tier,
            credits_remaining=db_record.credits_remaining,
            weekly_allowance=tier_config["weekly"],
            max_balance=tier_config["max"],
            gifts_sent_this_week=db_record.gifts_sent_this_week,
            max_gifts_per_week=tier_config["gift_limit"],
            credit_cycle_start=cycle_start,
            next_refresh=next_refresh,
            referral_code=db_record.referral_code,
        )

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
            db_record = self._get_db_record(user_id)
            return db_record.credits_remaining >= amount
        except CreditNotFoundError:
            return False

    def deduct_credit(
        self,
        user_id: str,
        amount: int,
        transaction_type: TransactionType,
        description: Optional[str] = None,
        related_user_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> CreditTransaction:
        """
        Deduct credits from user balance and log transaction.

        Args:
            user_id: Internal user UUID
            amount: Credits to deduct (positive number)
            transaction_type: Type of transaction
            description: Optional description
            related_user_id: Optional related user (for gifts)
            idempotency_key: Optional UUID to prevent duplicate processing

        Returns:
            CreditTransaction record

        Raises:
            InsufficientCreditsError: If user doesn't have enough credits
            CreditNotFoundError: If no credit record exists
        """
        db_record = self._get_db_record(user_id)

        if db_record.credits_remaining < amount:
            raise InsufficientCreditsError(
                user_id=user_id,
                required=amount,
                available=db_record.credits_remaining,
            )

        # Update balance
        new_remaining = db_record.credits_remaining - amount
        self.supabase.table("credits").update({"credits_remaining": new_remaining}).eq(
            "user_id", user_id
        ).execute()

        # Log transaction (negative amount for deduction)
        transaction_data = {
            "user_id": user_id,
            "amount": -amount,
            "transaction_type": transaction_type.value,
            "description": description,
            "related_user_id": related_user_id,
        }
        if idempotency_key:
            transaction_data["idempotency_key"] = idempotency_key

        result = self.supabase.table("credit_transactions").insert(transaction_data).execute()

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
        cap_at_max: bool = True,
        idempotency_key: Optional[str] = None,
    ) -> CreditTransaction:
        """
        Add credits to user balance and log transaction.

        Args:
            user_id: Internal user UUID
            amount: Credits to add (positive number)
            transaction_type: Type of transaction
            description: Optional description
            related_user_id: Optional related user (for gifts/referrals)
            cap_at_max: If True, cap at tier's max balance (2x weekly)
            idempotency_key: Optional UUID to prevent duplicate processing

        Returns:
            CreditTransaction record
        """
        db_record = self._get_db_record(user_id)
        tier_config = TIER_CONFIG[db_record.tier]

        # Calculate new balance, optionally capped
        new_remaining = db_record.credits_remaining + amount
        if cap_at_max:
            new_remaining = min(new_remaining, tier_config["max"])

        self.supabase.table("credits").update({"credits_remaining": new_remaining}).eq(
            "user_id", user_id
        ).execute()

        # Log transaction
        transaction_data = {
            "user_id": user_id,
            "amount": amount,
            "transaction_type": transaction_type.value,
            "description": description,
            "related_user_id": related_user_id,
        }
        if idempotency_key:
            transaction_data["idempotency_key"] = idempotency_key

        result = self.supabase.table("credit_transactions").insert(transaction_data).execute()

        if not result.data:
            raise CreditServiceError("Failed to create transaction record")

        return CreditTransaction(**result.data[0])

    def refund_credit(
        self,
        user_id: str,
        session_id: str,
        participant_id: str,
    ) -> Optional[CreditTransaction]:
        """
        Refund credit for a cancelled session.

        Checks credit_refunded_at to prevent double-refund.

        Args:
            user_id: User who cancelled
            session_id: Session being cancelled
            participant_id: session_participants.id record

        Returns:
            CreditTransaction if refunded, None if already refunded
        """
        # Check if already refunded
        participant = (
            self.supabase.table("session_participants")
            .select("credit_refunded_at, credit_transaction_id")
            .eq("id", participant_id)
            .single()
            .execute()
        )

        if participant.data.get("credit_refunded_at"):
            return None  # Already refunded

        # Add credit back
        transaction = self.add_credit(
            user_id=user_id,
            amount=1,
            transaction_type=TransactionType.REFUND,
            description=f"Cancelled session {session_id}",
            cap_at_max=False,  # Refunds should not be capped
        )

        # Mark as refunded
        self.supabase.table("session_participants").update(
            {"credit_refunded_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", participant_id).execute()

        return transaction

    def refresh_credits_for_user(self, user_id: str) -> Optional[CreditTransaction]:
        """
        Refresh credits for a user if their cycle has expired.

        Rolling 7-day refresh: new_balance = min(current + tier_weekly, tier_max)

        Args:
            user_id: User to refresh

        Returns:
            CreditTransaction if refreshed, None if not due
        """
        db_record = self._get_db_record(user_id)
        cycle_start = db_record.credit_cycle_start or datetime.now(timezone.utc).date()

        # Check if refresh is due
        if datetime.now(timezone.utc).date() < cycle_start + timedelta(days=7):
            return None  # Not due yet

        tier_config = TIER_CONFIG[db_record.tier]
        weekly_credits = tier_config["weekly"]
        max_balance = tier_config["max"]

        # Calculate new balance with rollover cap
        new_balance = min(db_record.credits_remaining + weekly_credits, max_balance)
        credits_added = new_balance - db_record.credits_remaining

        # Update balance and reset cycle
        self.supabase.table("credits").update(
            {
                "credits_remaining": new_balance,
                "credit_cycle_start": datetime.now(timezone.utc).date().isoformat(),
                "gifts_sent_this_week": 0,  # Reset gift counter too
            }
        ).eq("user_id", user_id).execute()

        # Log transaction
        transaction_data = {
            "user_id": user_id,
            "amount": credits_added,
            "transaction_type": TransactionType.WEEKLY_REFRESH.value,
            "description": f"Weekly refresh ({db_record.tier.value} tier)",
        }

        result = self.supabase.table("credit_transactions").insert(transaction_data).execute()

        if not result.data:
            raise CreditServiceError("Failed to create refresh transaction")

        return CreditTransaction(**result.data[0])

    def gift_credit(
        self,
        sender_id: str,
        recipient_id: str,
        amount: int = 1,
        idempotency_key: Optional[str] = None,
    ) -> GiftResponse:
        """
        Gift credits from one user to another.

        Business rules validated in Python, atomic money movement via SQL RPC.

        Args:
            sender_id: User gifting credits
            recipient_id: User receiving credits
            amount: Credits to gift (1-4)
            idempotency_key: Optional UUID to prevent duplicate processing

        Returns:
            GiftResponse with new sender balance

        Raises:
            GiftNotAllowedError: Sender's tier doesn't allow gifting
            GiftLimitExceededError: Weekly gift limit reached
            InsufficientCreditsError: Not enough credits to gift
            CreditNotFoundError: User not found
        """
        if sender_id == recipient_id:
            raise CreditServiceError("Cannot gift credits to yourself")

        # Python validates business rules
        sender_record = self._get_db_record(sender_id)
        tier_config = TIER_CONFIG[sender_record.tier]

        if not tier_config["can_gift"]:
            raise GiftNotAllowedError(sender_record.tier)

        if sender_record.gifts_sent_this_week + amount > tier_config["gift_limit"]:
            raise GiftLimitExceededError(
                sender_record.gifts_sent_this_week,
                tier_config["gift_limit"],
            )

        if sender_record.credits_remaining < amount:
            raise InsufficientCreditsError(
                user_id=sender_id,
                required=amount,
                available=sender_record.credits_remaining,
            )

        # Verify recipient exists
        try:
            self._get_db_record(recipient_id)
        except CreditNotFoundError:
            raise CreditNotFoundError(f"Recipient {recipient_id} not found")

        # Atomic money movement via SQL RPC
        rpc_params = {
            "p_sender_id": sender_id,
            "p_recipient_id": recipient_id,
            "p_amount": amount,
        }
        if idempotency_key:
            rpc_params["p_idempotency_key"] = idempotency_key

        try:
            result = self.supabase.rpc("atomic_transfer_credits", rpc_params).execute()
        except Exception as e:
            error_msg = str(e)
            if "INSUFFICIENT_CREDITS" in error_msg:
                raise InsufficientCreditsError(
                    user_id=sender_id,
                    required=amount,
                    available=sender_record.credits_remaining,
                )
            raise CreditServiceError(f"Transfer failed: {error_msg}")

        # Update sender's gift counter
        self.supabase.table("credits").update(
            {"gifts_sent_this_week": sender_record.gifts_sent_this_week + amount}
        ).eq("user_id", sender_id).execute()

        new_balance = result.data[0]["sender_new_balance"] if result.data else 0

        return GiftResponse(
            success=True,
            new_balance=new_balance,
            message=f"Successfully gifted {amount} credit(s)",
        )

    def get_referral_info(
        self, user_id: str, base_url: str = "https://focus-squad.com"
    ) -> ReferralInfo:
        """
        Get user's referral code and stats.

        Args:
            user_id: User to get info for
            base_url: Base URL for shareable link

        Returns:
            ReferralInfo with code, stats, and shareable link
        """
        db_record = self._get_db_record(user_id)

        # Get referrer's username if referred
        referred_by_username = None
        if db_record.referred_by:
            referrer = (
                self.supabase.table("users")
                .select("username")
                .eq("id", db_record.referred_by)
                .single()
                .execute()
            )
            if referrer.data:
                referred_by_username = referrer.data.get("username")

        return ReferralInfo(
            referral_code=db_record.referral_code or "",
            referrals_completed=db_record.referrals_completed,
            referred_by=referred_by_username,
            shareable_link=f"{base_url}/join?ref={db_record.referral_code}",
        )

    def apply_referral_code(self, user_id: str, referral_code: str) -> str:
        """
        Apply a referral code for a user.

        Args:
            user_id: User applying the code
            referral_code: Code to apply

        Returns:
            Referrer's username

        Raises:
            ReferralAlreadyAppliedError: User already has a referrer
            InvalidReferralCodeError: Code doesn't exist
            SelfReferralError: User tried to use their own code
        """
        db_record = self._get_db_record(user_id)

        if db_record.referred_by:
            raise ReferralAlreadyAppliedError("You have already used a referral code")

        if db_record.referral_code == referral_code:
            raise SelfReferralError("Cannot use your own referral code")

        # Find referrer by code
        referrer = (
            self.supabase.table("credits")
            .select("user_id")
            .eq("referral_code", referral_code)
            .execute()
        )

        if not referrer.data:
            raise InvalidReferralCodeError(f"Referral code '{referral_code}' not found")

        referrer_id = referrer.data[0]["user_id"]

        # Get referrer's username
        referrer_user = (
            self.supabase.table("users").select("username").eq("id", referrer_id).single().execute()
        )

        # Update user's referred_by
        self.supabase.table("credits").update({"referred_by": referrer_id}).eq(
            "user_id", user_id
        ).execute()

        return referrer_user.data.get("username", "Unknown")

    def award_referral_bonus(self, user_id: str) -> bool:
        """
        Award referral bonus if this is user's first completed session.

        Called when session ends. Awards +1 credit to both user and referrer.

        Args:
            user_id: User who completed session

        Returns:
            True if bonus was awarded, False if not eligible
        """
        db_record = self._get_db_record(user_id)

        # Check if user has a referrer
        if not db_record.referred_by:
            return False

        # Check if this is user's first completed session
        completed_sessions = (
            self.supabase.table("session_participants")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .is_("left_at", "null")  # Has completed (still present at session end)
            .execute()
        )

        # If more than 1 completed session, bonus already given
        if completed_sessions.count and completed_sessions.count > 1:
            return False

        # Award bonus to both parties
        self.add_credit(
            user_id=user_id,
            amount=1,
            transaction_type=TransactionType.REFERRAL,
            description="First session bonus",
            related_user_id=db_record.referred_by,
            cap_at_max=False,
        )

        self.add_credit(
            user_id=db_record.referred_by,
            amount=1,
            transaction_type=TransactionType.REFERRAL,
            description=f"Referral bonus: {user_id} completed first session",
            related_user_id=user_id,
            cap_at_max=False,
        )

        # Increment referrer's referrals_completed
        self.supabase.table("credits").update(
            {"referrals_completed": db_record.referrals_completed + 1}
        ).eq("user_id", db_record.referred_by).execute()

        return True
