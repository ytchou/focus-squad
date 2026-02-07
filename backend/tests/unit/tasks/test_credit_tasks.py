"""Unit tests for credit tasks (daily refresh + single-user refresh).

Tests:
- refresh_due_credits: batch refresh for users with expired 7-day cycles
- refresh_single_user_credits: on-demand refresh for a single user
"""

from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# refresh_due_credits() Tests
# =============================================================================


class TestRefreshDueCredits:
    """Tests for the daily batch credit refresh task."""

    @pytest.mark.unit
    def test_no_users_due(self) -> None:
        """Returns zero counts when no users are due for refresh."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value.lte.return_value.execute.return_value.data = []
        mock_supabase.table.return_value = mock_table

        with patch("app.tasks.credit_tasks.get_supabase", return_value=mock_supabase):
            with patch("app.tasks.credit_tasks.CreditService"):
                from app.tasks.credit_tasks import refresh_due_credits

                result = refresh_due_credits()

        assert result == {"refreshed_count": 0, "errors": 0}

    @pytest.mark.unit
    def test_refreshes_multiple_users(self) -> None:
        """Counts only users who actually got refreshed (transaction returned)."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value.lte.return_value.execute.return_value.data = [
            {"user_id": "user-1", "credit_cycle_start": "2025-01-01"},
            {"user_id": "user-2", "credit_cycle_start": "2025-01-01"},
        ]
        mock_supabase.table.return_value = mock_table

        mock_transaction = MagicMock()
        mock_transaction.amount = 2

        with patch("app.tasks.credit_tasks.get_supabase", return_value=mock_supabase):
            with patch("app.tasks.credit_tasks.CreditService") as MockCreditService:
                mock_service = MockCreditService.return_value
                # User 1 gets refreshed, user 2 is not due (returns None)
                mock_service.refresh_credits_for_user.side_effect = [
                    mock_transaction,
                    None,
                ]

                from app.tasks.credit_tasks import refresh_due_credits

                result = refresh_due_credits()

        assert result == {"refreshed_count": 1, "errors": 0}
        assert mock_service.refresh_credits_for_user.call_count == 2

    @pytest.mark.unit
    def test_handles_refresh_errors(self) -> None:
        """Counts errors when refresh_credits_for_user raises an exception."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value.lte.return_value.execute.return_value.data = [
            {"user_id": "user-1", "credit_cycle_start": "2025-01-01"},
        ]
        mock_supabase.table.return_value = mock_table

        with patch("app.tasks.credit_tasks.get_supabase", return_value=mock_supabase):
            with patch("app.tasks.credit_tasks.CreditService") as MockCreditService:
                mock_service = MockCreditService.return_value
                mock_service.refresh_credits_for_user.side_effect = Exception("DB connection lost")

                from app.tasks.credit_tasks import refresh_due_credits

                result = refresh_due_credits()

        assert result == {"refreshed_count": 0, "errors": 1}


# =============================================================================
# refresh_single_user_credits() Tests
# =============================================================================


class TestRefreshSingleUserCredits:
    """Tests for on-demand single-user credit refresh task."""

    @pytest.mark.unit
    def test_refreshed_successfully(self) -> None:
        """Returns success with amount when user credits are refreshed."""
        mock_transaction = MagicMock()
        mock_transaction.amount = 2

        with patch("app.tasks.credit_tasks.CreditService") as MockCreditService:
            mock_service = MockCreditService.return_value
            mock_service.refresh_credits_for_user.return_value = mock_transaction

            from app.tasks.credit_tasks import refresh_single_user_credits

            result = refresh_single_user_credits("user-123")

        assert result == {"success": True, "refreshed": True, "amount_added": 2}

    @pytest.mark.unit
    def test_not_due_for_refresh(self) -> None:
        """Returns success with refreshed=False when user is not due."""
        with patch("app.tasks.credit_tasks.CreditService") as MockCreditService:
            mock_service = MockCreditService.return_value
            mock_service.refresh_credits_for_user.return_value = None

            from app.tasks.credit_tasks import refresh_single_user_credits

            result = refresh_single_user_credits("user-456")

        assert result["success"] is True
        assert result["refreshed"] is False
        assert "message" in result

    @pytest.mark.unit
    def test_handles_error(self) -> None:
        """Returns failure with error message when exception occurs."""
        with patch("app.tasks.credit_tasks.CreditService") as MockCreditService:
            mock_service = MockCreditService.return_value
            mock_service.refresh_credits_for_user.side_effect = Exception("Service unavailable")

            from app.tasks.credit_tasks import refresh_single_user_credits

            result = refresh_single_user_credits("user-789")

        assert result["success"] is False
        assert "Service unavailable" in result["error"]
