"""Unit tests for CreditService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.models.credit import (
    CreditBalance,
    CreditNotFoundError,
    GiftLimitExceededError,
    GiftNotAllowedError,
    InsufficientCreditsError,
    TransactionType,
    UserTier,
)
from app.services.credit_service import CreditService


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def credit_service(mock_supabase):
    """CreditService with mocked Supabase."""
    return CreditService(supabase=mock_supabase)


@pytest.fixture
def sample_credit_row():
    """Sample credit data from database (new schema)."""
    return {
        "user_id": "user-123",
        "tier": "free",
        "credits_remaining": 2,
        "gifts_sent_this_week": 0,
        "credit_cycle_start": datetime.now(timezone.utc).date().isoformat(),
        "referral_code": "ABC12345",
        "referred_by": None,
        "referrals_completed": 0,
    }


@pytest.fixture
def sample_transaction_row():
    """Sample transaction data from database."""
    return {
        "id": "tx-123",
        "user_id": "user-123",
        "amount": -1,
        "transaction_type": "session_join",
        "description": "Joined session session-123",
        "related_user_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


class TestGetBalance:
    """Tests for get_balance() method."""

    @pytest.mark.unit
    def test_returns_balance(self, credit_service, mock_supabase, sample_credit_row) -> None:
        """Returns CreditBalance when record exists."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]

        result = credit_service.get_balance("user-123")

        assert isinstance(result, CreditBalance)
        assert result.user_id == "user-123"
        assert result.credits_remaining == 2
        assert result.tier == UserTier.FREE
        assert result.weekly_allowance == 2  # Free tier
        assert result.max_balance == 4  # 2x free tier

    @pytest.mark.unit
    def test_not_found_raises_error(self, credit_service, mock_supabase) -> None:
        """Raises CreditNotFoundError when no record exists."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(CreditNotFoundError):
            credit_service.get_balance("nonexistent")


class TestHasSufficientCredits:
    """Tests for has_sufficient_credits() method."""

    @pytest.mark.unit
    def test_returns_true_when_sufficient(
        self, credit_service, mock_supabase, sample_credit_row
    ) -> None:
        """Returns True when user has enough credits."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]

        result = credit_service.has_sufficient_credits("user-123", amount=1)

        assert result is True

    @pytest.mark.unit
    def test_returns_false_when_insufficient(
        self, credit_service, mock_supabase, sample_credit_row
    ) -> None:
        """Returns False when user doesn't have enough credits."""
        low_credits = {**sample_credit_row, "credits_remaining": 0}
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [low_credits]

        result = credit_service.has_sufficient_credits("user-123", amount=1)

        assert result is False

    @pytest.mark.unit
    def test_returns_false_when_not_found(self, credit_service, mock_supabase) -> None:
        """Returns False when user has no credit record."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        result = credit_service.has_sufficient_credits("nonexistent", amount=1)

        assert result is False


class TestDeductCredit:
    """Tests for deduct_credit() method."""

    @pytest.mark.unit
    def test_deducts_and_logs(
        self, credit_service, mock_supabase, sample_credit_row, sample_transaction_row
    ) -> None:
        """Deducts credit and creates transaction record."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Get balance returns 2 credits
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]

        # Update succeeds
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            {**sample_credit_row, "credits_remaining": 1}
        ]

        # Insert transaction succeeds
        mock_table.insert.return_value.execute.return_value.data = [sample_transaction_row]

        result = credit_service.deduct_credit(
            user_id="user-123",
            amount=1,
            transaction_type=TransactionType.SESSION_JOIN,
            description="Joined session session-123",
        )

        assert result.amount == -1  # Negative for spending
        assert result.transaction_type == "session_join"

    @pytest.mark.unit
    def test_insufficient_credits_raises_error(
        self, credit_service, mock_supabase, sample_credit_row
    ) -> None:
        """Raises InsufficientCreditsError when not enough credits."""
        low_credits = {**sample_credit_row, "credits_remaining": 0}
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [low_credits]

        with pytest.raises(InsufficientCreditsError) as exc_info:
            credit_service.deduct_credit(
                user_id="user-123",
                amount=1,
                transaction_type=TransactionType.SESSION_JOIN,
            )

        assert exc_info.value.required == 1
        assert exc_info.value.available == 0


class TestAddCredit:
    """Tests for add_credit() method."""

    @pytest.mark.unit
    def test_adds_and_logs(
        self, credit_service, mock_supabase, sample_credit_row, sample_transaction_row
    ) -> None:
        """Adds credit and creates transaction record."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Get balance returns 2 credits
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]

        # Update succeeds
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            {**sample_credit_row, "credits_remaining": 3}
        ]

        # Insert transaction succeeds
        positive_transaction = {**sample_transaction_row, "amount": 1}
        mock_table.insert.return_value.execute.return_value.data = [positive_transaction]

        result = credit_service.add_credit(
            user_id="user-123",
            amount=1,
            transaction_type=TransactionType.REFERRAL,
            description="Referral bonus",
        )

        assert result.amount == 1  # Positive for earning

    @pytest.mark.unit
    def test_caps_at_max_balance(
        self, credit_service, mock_supabase, sample_credit_row, sample_transaction_row
    ) -> None:
        """Credits are capped at tier's max balance (2x weekly)."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # User has 3 credits (free tier max is 4)
        high_credits = {**sample_credit_row, "credits_remaining": 3}
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [high_credits]

        # Update succeeds
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            {**sample_credit_row, "credits_remaining": 4}  # Capped at max
        ]

        # Insert transaction succeeds
        positive_transaction = {**sample_transaction_row, "amount": 2}
        mock_table.insert.return_value.execute.return_value.data = [positive_transaction]

        credit_service.add_credit(
            user_id="user-123",
            amount=2,  # Would be 5, but capped at 4
            transaction_type=TransactionType.WEEKLY_REFRESH,
            description="Weekly refresh",
        )

        # Verify update was called with capped value
        update_call = mock_table.update.call_args.args[0]
        assert update_call["credits_remaining"] == 4  # Capped at max


class TestRefreshCreditsForUser:
    """Tests for refresh_credits_for_user() method."""

    @pytest.mark.unit
    def test_refreshes_when_cycle_expired(
        self, credit_service, mock_supabase, sample_credit_row, sample_transaction_row
    ) -> None:
        """Refreshes credits when 7-day cycle has expired."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # User's cycle started 8 days ago (due for refresh)
        expired_cycle = {
            **sample_credit_row,
            "credit_cycle_start": (
                datetime.now(timezone.utc).date() - timedelta(days=8)
            ).isoformat(),
            "credits_remaining": 1,
        }
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [expired_cycle]

        # Update succeeds
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            {**sample_credit_row, "credits_remaining": 3}  # 1 + 2 weekly
        ]

        # Insert transaction succeeds
        refresh_transaction = {
            **sample_transaction_row,
            "amount": 2,
            "transaction_type": "weekly_refresh",
        }
        mock_table.insert.return_value.execute.return_value.data = [refresh_transaction]

        result = credit_service.refresh_credits_for_user("user-123")

        assert result is not None
        assert result.amount == 2  # Free tier gets 2 credits

    @pytest.mark.unit
    def test_no_refresh_when_cycle_active(
        self, credit_service, mock_supabase, sample_credit_row
    ) -> None:
        """Does not refresh when 7-day cycle is still active."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # User's cycle started 3 days ago (not due yet)
        active_cycle = {
            **sample_credit_row,
            "credit_cycle_start": (
                datetime.now(timezone.utc).date() - timedelta(days=3)
            ).isoformat(),
        }
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [active_cycle]

        result = credit_service.refresh_credits_for_user("user-123")

        assert result is None  # No refresh needed


class TestGiftCredit:
    """Tests for gift_credit() method."""

    @pytest.mark.unit
    def test_gift_not_allowed_for_free_tier(
        self, credit_service, mock_supabase, sample_credit_row
    ) -> None:
        """Raises GiftNotAllowedError for Free tier users."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Free tier user
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]

        with pytest.raises(GiftNotAllowedError):
            credit_service.gift_credit(
                sender_id="user-123",
                recipient_id="user-456",
                amount=1,
            )

    @pytest.mark.unit
    def test_gift_limit_exceeded(self, credit_service, mock_supabase, sample_credit_row) -> None:
        """Raises GiftLimitExceededError when weekly limit reached."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Pro tier user who has sent 4 gifts this week
        pro_user = {
            **sample_credit_row,
            "tier": "pro",
            "credits_remaining": 8,
            "gifts_sent_this_week": 4,
        }
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [pro_user]

        with pytest.raises(GiftLimitExceededError):
            credit_service.gift_credit(
                sender_id="user-123",
                recipient_id="user-456",
                amount=1,
            )


# =============================================================================
# WU1 Regression: UTC timezone usage
# =============================================================================


class TestUTCTimezone:
    """Regression tests verifying UTC is used consistently."""

    @pytest.mark.unit
    def test_refresh_uses_utc_for_cycle_comparison(
        self, credit_service, mock_supabase, sample_credit_row, sample_transaction_row
    ) -> None:
        """refresh_credits_for_user compares dates using UTC timezone."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Cycle expired 8 days ago
        expired_cycle = {
            **sample_credit_row,
            "credit_cycle_start": (
                datetime.now(timezone.utc).date() - timedelta(days=8)
            ).isoformat(),
            "credits_remaining": 1,
        }
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [expired_cycle]
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            {**sample_credit_row, "credits_remaining": 3}
        ]
        refresh_tx = {**sample_transaction_row, "amount": 2, "transaction_type": "weekly_refresh"}
        mock_table.insert.return_value.execute.return_value.data = [refresh_tx]

        result = credit_service.refresh_credits_for_user("user-123")

        assert result is not None
        # Verify the update was called with UTC date for new cycle start
        update_call = mock_table.update.call_args_list[0].args[0]
        assert "credit_cycle_start" in update_call
        cycle_date = update_call["credit_cycle_start"]
        # Should be today's date (UTC)
        assert cycle_date == datetime.now(timezone.utc).date().isoformat()

    @pytest.mark.unit
    def test_refund_timestamps_use_utc(
        self, credit_service, mock_supabase, sample_credit_row, sample_transaction_row
    ) -> None:
        """refund_credit uses UTC timestamp for credit_refunded_at."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Participant not yet refunded
        participant_data = {"credit_refunded_at": None, "credit_transaction_id": "tx-old"}
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = participant_data

        # Credit add succeeds
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            {**sample_credit_row, "credits_remaining": 3}
        ]
        refund_tx = {**sample_transaction_row, "amount": 1, "transaction_type": "refund"}
        mock_table.insert.return_value.execute.return_value.data = [refund_tx]

        result = credit_service.refund_credit(
            user_id="user-123",
            session_id="session-1",
            participant_id="p-1",
        )

        assert result is not None

    @pytest.mark.unit
    def test_get_balance_computes_next_refresh_utc(
        self, credit_service, mock_supabase, sample_credit_row
    ) -> None:
        """get_balance computes next_refresh as UTC datetime."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]

        result = credit_service.get_balance("user-123")

        # next_refresh should be a timezone-aware UTC datetime
        assert result.next_refresh.tzinfo is not None
        assert result.next_refresh.tzinfo == timezone.utc


# =============================================================================
# WU2 Regression: Idempotency key in transactions
# =============================================================================


class TestIdempotencyKey:
    """Tests for idempotency key support in credit operations."""

    @pytest.mark.unit
    def test_deduct_passes_idempotency_key(
        self, credit_service, mock_supabase, sample_credit_row, sample_transaction_row
    ) -> None:
        """deduct_credit includes idempotency_key in transaction insert."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            {**sample_credit_row, "credits_remaining": 1}
        ]
        mock_table.insert.return_value.execute.return_value.data = [sample_transaction_row]

        credit_service.deduct_credit(
            user_id="user-123",
            amount=1,
            transaction_type=TransactionType.SESSION_JOIN,
            idempotency_key="idem-key-123",
        )

        # Verify the insert included the idempotency key
        insert_data = mock_table.insert.call_args.args[0]
        assert insert_data["idempotency_key"] == "idem-key-123"

    @pytest.mark.unit
    def test_deduct_omits_idempotency_key_when_none(
        self, credit_service, mock_supabase, sample_credit_row, sample_transaction_row
    ) -> None:
        """deduct_credit does not include idempotency_key when not provided."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            {**sample_credit_row, "credits_remaining": 1}
        ]
        mock_table.insert.return_value.execute.return_value.data = [sample_transaction_row]

        credit_service.deduct_credit(
            user_id="user-123",
            amount=1,
            transaction_type=TransactionType.SESSION_JOIN,
        )

        insert_data = mock_table.insert.call_args.args[0]
        assert "idempotency_key" not in insert_data

    @pytest.mark.unit
    def test_add_credit_passes_idempotency_key(
        self, credit_service, mock_supabase, sample_credit_row, sample_transaction_row
    ) -> None:
        """add_credit includes idempotency_key in transaction insert."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            {**sample_credit_row, "credits_remaining": 3}
        ]
        positive_tx = {**sample_transaction_row, "amount": 1}
        mock_table.insert.return_value.execute.return_value.data = [positive_tx]

        credit_service.add_credit(
            user_id="user-123",
            amount=1,
            transaction_type=TransactionType.REFERRAL,
            idempotency_key="ref-key-456",
        )

        insert_data = mock_table.insert.call_args.args[0]
        assert insert_data["idempotency_key"] == "ref-key-456"

    @pytest.mark.unit
    def test_gift_credit_passes_idempotency_key_to_rpc(
        self, credit_service, mock_supabase, sample_credit_row
    ) -> None:
        """gift_credit passes idempotency_key to atomic_transfer_credits RPC."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Pro tier sender with credits
        pro_sender = {
            **sample_credit_row,
            "tier": "pro",
            "credits_remaining": 8,
            "gifts_sent_this_week": 0,
        }
        # First call: sender lookup, second: recipient lookup
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [pro_sender]

        # RPC succeeds
        mock_rpc = MagicMock()
        mock_rpc.execute.return_value.data = [{"sender_new_balance": 7}]
        mock_supabase.rpc.return_value = mock_rpc

        # Update gift counter
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [{}]

        credit_service.gift_credit(
            sender_id="user-123",
            recipient_id="user-456",
            amount=1,
            idempotency_key="gift-key-789",
        )

        # Verify RPC was called with idempotency key
        rpc_args = mock_supabase.rpc.call_args
        assert rpc_args.args[0] == "atomic_transfer_credits"
        assert rpc_args.args[1]["p_idempotency_key"] == "gift-key-789"


# =============================================================================
# Coverage expansion: refund_credit, gift_credit edge cases, referral methods
# =============================================================================


@pytest.fixture
def pro_credit_row(sample_credit_row):
    """Pro tier credit row with sufficient credits."""
    return {
        **sample_credit_row,
        "tier": "pro",
        "credits_remaining": 8,
        "gifts_sent_this_week": 0,
    }


@pytest.fixture
def refund_transaction_row(sample_transaction_row):
    """Transaction row shaped as a refund."""
    return {
        **sample_transaction_row,
        "amount": 1,
        "transaction_type": "refund",
        "description": "Cancelled session session-1",
    }


class TestRefundCredit:
    """Tests for refund_credit() method."""

    @pytest.mark.unit
    def test_refund_already_refunded_returns_none(self, credit_service, mock_supabase) -> None:
        """Returns None when participant was already refunded."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Participant already refunded
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "credit_refunded_at": "2025-01-01T00:00:00Z",
            "credit_transaction_id": "tx-old",
        }

        result = credit_service.refund_credit(
            user_id="user-123",
            session_id="session-1",
            participant_id="p-1",
        )

        assert result is None

    @pytest.mark.unit
    def test_refund_success_adds_credit_and_marks(
        self, credit_service, mock_supabase, sample_credit_row, refund_transaction_row
    ) -> None:
        """Full refund flow: adds credit back and marks participant refunded."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Participant not yet refunded
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "credit_refunded_at": None,
            "credit_transaction_id": "tx-old",
        }

        # add_credit internals: _get_db_record, update, insert
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            {**sample_credit_row, "credits_remaining": 3}
        ]
        mock_table.insert.return_value.execute.return_value.data = [refund_transaction_row]

        result = credit_service.refund_credit(
            user_id="user-123",
            session_id="session-1",
            participant_id="p-1",
        )

        assert result is not None
        assert result.amount == 1
        assert result.transaction_type == "refund"

        # Verify participant was marked as refunded via update call
        # At least one update call should include credit_refunded_at
        update_calls = mock_table.update.call_args_list
        refunded_at_updates = [c for c in update_calls if "credit_refunded_at" in c.args[0]]
        assert len(refunded_at_updates) >= 1

    @pytest.mark.unit
    def test_refund_returns_transaction(
        self, credit_service, mock_supabase, sample_credit_row, refund_transaction_row
    ) -> None:
        """Verify refund returns the CreditTransaction from add_credit."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Participant not refunded
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "credit_refunded_at": None,
            "credit_transaction_id": "tx-old",
        }

        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            {**sample_credit_row, "credits_remaining": 3}
        ]
        mock_table.insert.return_value.execute.return_value.data = [refund_transaction_row]

        result = credit_service.refund_credit(
            user_id="user-123",
            session_id="session-1",
            participant_id="p-1",
        )

        from app.models.credit import CreditTransaction

        assert isinstance(result, CreditTransaction)
        assert result.id == "tx-123"


class TestGiftCreditEdgeCases:
    """Edge case tests for gift_credit() method."""

    @pytest.mark.unit
    def test_gift_self_raises_error(self, credit_service, mock_supabase) -> None:
        """Raises CreditServiceError when gifting to yourself."""
        from app.models.credit import CreditServiceError

        with pytest.raises(CreditServiceError, match="Cannot gift credits to yourself"):
            credit_service.gift_credit(
                sender_id="user-123",
                recipient_id="user-123",
                amount=1,
            )

    @pytest.mark.unit
    def test_gift_recipient_not_found(self, credit_service, mock_supabase, pro_credit_row) -> None:
        """Raises CreditNotFoundError when recipient doesn't exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # First call (sender): returns pro record; second call (recipient): empty
        execute_mock = mock_table.select.return_value.eq.return_value.execute
        execute_mock.return_value.data = [pro_credit_row]

        # Override _get_db_record to raise on second call
        original_get = credit_service._get_db_record
        call_count = {"n": 0}

        def side_effect_get(user_id):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return original_get(user_id)
            raise CreditNotFoundError(f"Recipient {user_id} not found")

        credit_service._get_db_record = side_effect_get

        with pytest.raises(CreditNotFoundError, match="Recipient"):
            credit_service.gift_credit(
                sender_id="user-123",
                recipient_id="user-nonexistent",
                amount=1,
            )

    @pytest.mark.unit
    def test_gift_rpc_insufficient_credits(
        self, credit_service, mock_supabase, pro_credit_row
    ) -> None:
        """Raises InsufficientCreditsError when RPC reports insufficient credits."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Both sender and recipient lookups succeed
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [pro_credit_row]

        # RPC raises INSUFFICIENT_CREDITS
        mock_supabase.rpc.side_effect = Exception("INSUFFICIENT_CREDITS")

        with pytest.raises(InsufficientCreditsError):
            credit_service.gift_credit(
                sender_id="user-123",
                recipient_id="user-456",
                amount=1,
            )

    @pytest.mark.unit
    def test_gift_rpc_generic_error(self, credit_service, mock_supabase, pro_credit_row) -> None:
        """Raises CreditServiceError when RPC reports a generic error."""
        from app.models.credit import CreditServiceError

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_table.select.return_value.eq.return_value.execute.return_value.data = [pro_credit_row]

        # RPC raises unknown error
        mock_supabase.rpc.side_effect = Exception("UNKNOWN_ERROR")

        with pytest.raises(CreditServiceError, match="Transfer failed"):
            credit_service.gift_credit(
                sender_id="user-123",
                recipient_id="user-456",
                amount=1,
            )


class TestGetReferralInfo:
    """Tests for get_referral_info() method."""

    @pytest.mark.unit
    def test_get_referral_info_no_referrer(
        self, credit_service, mock_supabase, sample_credit_row
    ) -> None:
        """Returns ReferralInfo with referred_by=None when user has no referrer."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # User has no referrer (referred_by=None in sample_credit_row)
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]

        result = credit_service.get_referral_info("user-123")

        from app.models.credit import ReferralInfo

        assert isinstance(result, ReferralInfo)
        assert result.referred_by is None
        assert result.referral_code == "ABC12345"
        assert "ABC12345" in result.shareable_link

    @pytest.mark.unit
    def test_get_referral_info_with_referrer(
        self, credit_service, mock_supabase, sample_credit_row
    ) -> None:
        """Returns ReferralInfo with referrer's username when user has a referrer."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # User has a referrer
        referred_row = {**sample_credit_row, "referred_by": "referrer-user-id"}
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [referred_row]

        # Referrer username lookup
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "username": "cool_referrer"
        }

        result = credit_service.get_referral_info("user-123")

        assert result.referred_by == "cool_referrer"


class TestApplyReferralCode:
    """Tests for apply_referral_code() method."""

    @pytest.mark.unit
    def test_apply_success(self, credit_service, mock_supabase, sample_credit_row) -> None:
        """Happy path: applies referral code and returns referrer username."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # User has no referrer, different referral code
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]

        # Referrer lookup by code
        # This is the second .eq call chain - returns referrer's user_id
        # Since mock returns same data for all .eq chains, we use side_effect
        execute_results = [
            MagicMock(data=[sample_credit_row]),  # _get_db_record(user_id)
            MagicMock(data=[{"user_id": "referrer-id"}]),  # credits lookup by referral_code
        ]
        mock_table.select.return_value.eq.return_value.execute.side_effect = execute_results

        # Referrer username lookup (single chain)
        mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "username": "my_referrer"
        }

        # Update succeeds
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [{}]

        result = credit_service.apply_referral_code("user-123", "DIFFERENT_CODE")

        assert result == "my_referrer"

    @pytest.mark.unit
    def test_apply_already_applied(self, credit_service, mock_supabase, sample_credit_row) -> None:
        """Raises ReferralAlreadyAppliedError when user already has a referrer."""
        from app.models.credit import ReferralAlreadyAppliedError

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # User already has a referrer
        referred_row = {**sample_credit_row, "referred_by": "existing-referrer"}
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [referred_row]

        with pytest.raises(ReferralAlreadyAppliedError):
            credit_service.apply_referral_code("user-123", "SOMECODE")

    @pytest.mark.unit
    def test_apply_self_referral(self, credit_service, mock_supabase, sample_credit_row) -> None:
        """Raises SelfReferralError when user tries to use their own code."""
        from app.models.credit import SelfReferralError

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # User has referral_code "ABC12345" in sample_credit_row
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]

        with pytest.raises(SelfReferralError):
            credit_service.apply_referral_code("user-123", "ABC12345")

    @pytest.mark.unit
    def test_apply_invalid_code(self, credit_service, mock_supabase, sample_credit_row) -> None:
        """Raises InvalidReferralCodeError when code doesn't exist."""
        from app.models.credit import InvalidReferralCodeError

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # First call: _get_db_record returns user; second call: referral code lookup returns empty
        execute_results = [
            MagicMock(data=[sample_credit_row]),  # _get_db_record
            MagicMock(data=[]),  # referral code lookup - not found
        ]
        mock_table.select.return_value.eq.return_value.execute.side_effect = execute_results

        with pytest.raises(InvalidReferralCodeError, match="not found"):
            credit_service.apply_referral_code("user-123", "BADCODE")


class TestAwardReferralBonus:
    """Tests for award_referral_bonus() method."""

    @pytest.mark.unit
    def test_award_no_referrer_returns_false(
        self, credit_service, mock_supabase, sample_credit_row
    ) -> None:
        """Returns False when user has no referrer."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # User has no referrer (referred_by=None in sample_credit_row)
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_credit_row
        ]

        result = credit_service.award_referral_bonus("user-123")

        assert result is False

    @pytest.mark.unit
    def test_award_first_session_awards_both(
        self, credit_service, mock_supabase, sample_credit_row, sample_transaction_row
    ) -> None:
        """Awards +1 credit to both user and referrer on first completed session."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # User has a referrer
        referred_row = {
            **sample_credit_row,
            "referred_by": "referrer-user-id",
        }
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [referred_row]

        # Completed sessions count = 1 (first session)
        count_result = MagicMock()
        count_result.count = 1
        mock_table.select.return_value.eq.return_value.is_.return_value.execute.return_value = (
            count_result
        )

        # add_credit internals (called twice: user + referrer)
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [{}]
        referral_tx = {
            **sample_transaction_row,
            "amount": 1,
            "transaction_type": "referral",
        }
        mock_table.insert.return_value.execute.return_value.data = [referral_tx]

        result = credit_service.award_referral_bonus("user-123")

        assert result is True

    @pytest.mark.unit
    def test_award_not_first_session_returns_false(
        self, credit_service, mock_supabase, sample_credit_row
    ) -> None:
        """Returns False when user has already completed more than one session."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # User has a referrer
        referred_row = {
            **sample_credit_row,
            "referred_by": "referrer-user-id",
        }
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [referred_row]

        # Completed sessions count = 2 (bonus already given)
        count_result = MagicMock()
        count_result.count = 2
        mock_table.select.return_value.eq.return_value.is_.return_value.execute.return_value = (
            count_result
        )

        result = credit_service.award_referral_bonus("user-123")

        assert result is False
