"""Unit tests for CreditService."""

from datetime import date, datetime, timedelta, timezone
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
        "credit_cycle_start": date.today().isoformat(),
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
    def test_returns_balance(self, credit_service, mock_supabase, sample_credit_row):
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
    def test_not_found_raises_error(self, credit_service, mock_supabase):
        """Raises CreditNotFoundError when no record exists."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(CreditNotFoundError):
            credit_service.get_balance("nonexistent")


class TestHasSufficientCredits:
    """Tests for has_sufficient_credits() method."""

    @pytest.mark.unit
    def test_returns_true_when_sufficient(self, credit_service, mock_supabase, sample_credit_row):
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
    ):
        """Returns False when user doesn't have enough credits."""
        low_credits = {**sample_credit_row, "credits_remaining": 0}
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [low_credits]

        result = credit_service.has_sufficient_credits("user-123", amount=1)

        assert result is False

    @pytest.mark.unit
    def test_returns_false_when_not_found(self, credit_service, mock_supabase):
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
    ):
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
    ):
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
    ):
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
    ):
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
        update_call = mock_table.update.call_args[0][0]
        assert update_call["credits_remaining"] == 4  # Capped at max


class TestRefreshCreditsForUser:
    """Tests for refresh_credits_for_user() method."""

    @pytest.mark.unit
    def test_refreshes_when_cycle_expired(
        self, credit_service, mock_supabase, sample_credit_row, sample_transaction_row
    ):
        """Refreshes credits when 7-day cycle has expired."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # User's cycle started 8 days ago (due for refresh)
        expired_cycle = {
            **sample_credit_row,
            "credit_cycle_start": (date.today() - timedelta(days=8)).isoformat(),
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
    def test_no_refresh_when_cycle_active(self, credit_service, mock_supabase, sample_credit_row):
        """Does not refresh when 7-day cycle is still active."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # User's cycle started 3 days ago (not due yet)
        active_cycle = {
            **sample_credit_row,
            "credit_cycle_start": (date.today() - timedelta(days=3)).isoformat(),
        }
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [active_cycle]

        result = credit_service.refresh_credits_for_user("user-123")

        assert result is None  # No refresh needed


class TestGiftCredit:
    """Tests for gift_credit() method."""

    @pytest.mark.unit
    def test_gift_not_allowed_for_free_tier(self, credit_service, mock_supabase, sample_credit_row):
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
    def test_gift_limit_exceeded(self, credit_service, mock_supabase, sample_credit_row):
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
