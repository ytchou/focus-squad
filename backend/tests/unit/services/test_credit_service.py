"""Unit tests for CreditService."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.services.credit_service import (
    CreditBalance,
    CreditNotFoundError,
    CreditService,
    InsufficientCreditsError,
    TransactionType,
    UserTier,
)


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
    """Sample credit data from database."""
    return {
        "user_id": "user-123",
        "tier": "free",
        "credits_remaining": 2,
        "credits_used_this_week": 0,
        "week_start_date": datetime.now(timezone.utc).isoformat(),
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
            {**sample_credit_row, "credits_remaining": 1, "credits_used_this_week": 1}
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
