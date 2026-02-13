"""Unit tests for rating tasks (expired pending_ratings cleanup).

Tests:
- cleanup_expired_pending_ratings: removes expired uncompleted records
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# cleanup_expired_pending_ratings() Tests
# =============================================================================


class TestCleanupExpiredPendingRatings:
    """Tests for the daily expired pending_ratings cleanup task."""

    @pytest.mark.unit
    def test_deletes_expired_uncompleted(self) -> None:
        """Deletes expired pending_ratings where completed_at is null."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        # Simulate 3 records deleted
        mock_table.delete.return_value.is_.return_value.lt.return_value.execute.return_value.data = [
            {"id": "pr-1"},
            {"id": "pr-2"},
            {"id": "pr-3"},
        ]
        mock_supabase.table.return_value = mock_table

        with patch("app.tasks.rating_tasks.get_supabase", return_value=mock_supabase):
            from app.tasks.rating_tasks import cleanup_expired_pending_ratings

            result = cleanup_expired_pending_ratings()

        assert result == {"deleted_count": 3}

        # Verify delete chain
        mock_table.delete.assert_called_once()
        mock_table.delete.return_value.is_.assert_called_once_with("completed_at", "null")

    @pytest.mark.unit
    def test_preserves_completed_ratings(self) -> None:
        """Does not delete pending_ratings that have completed_at set."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        # The is_("completed_at", "null") filter means completed ones won't match
        mock_table.delete.return_value.is_.return_value.lt.return_value.execute.return_value.data = []
        mock_supabase.table.return_value = mock_table

        with patch("app.tasks.rating_tasks.get_supabase", return_value=mock_supabase):
            from app.tasks.rating_tasks import cleanup_expired_pending_ratings

            result = cleanup_expired_pending_ratings()

        assert result == {"deleted_count": 0}

    @pytest.mark.unit
    def test_preserves_non_expired_ratings(self) -> None:
        """Does not delete pending_ratings where expires_at is in the future."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        # The lt("expires_at", now) filter means non-expired ones won't match
        mock_table.delete.return_value.is_.return_value.lt.return_value.execute.return_value.data = []
        mock_supabase.table.return_value = mock_table

        with patch("app.tasks.rating_tasks.get_supabase", return_value=mock_supabase):
            from app.tasks.rating_tasks import cleanup_expired_pending_ratings

            result = cleanup_expired_pending_ratings()

        assert result == {"deleted_count": 0}

    @pytest.mark.unit
    def test_compares_expires_at_with_current_time(self) -> None:
        """Verifies lt() is called with a timestamp close to now."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_table.delete.return_value.is_.return_value.lt.return_value.execute.return_value.data = []
        mock_supabase.table.return_value = mock_table

        before = datetime.now(timezone.utc)

        with patch("app.tasks.rating_tasks.get_supabase", return_value=mock_supabase):
            from app.tasks.rating_tasks import cleanup_expired_pending_ratings

            cleanup_expired_pending_ratings()

        after = datetime.now(timezone.utc)

        # Get the timestamp used in lt()
        lt_call = mock_table.delete.return_value.is_.return_value.lt
        lt_call.assert_called_once()
        call_args = lt_call.call_args.args
        assert call_args[0] == "expires_at"

        # Verify the timestamp is between before and after
        used_time = datetime.fromisoformat(call_args[1])
        assert before <= used_time <= after

    @pytest.mark.unit
    def test_returns_empty_data_as_zero(self) -> None:
        """Returns 0 when data is None or empty."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_table.delete.return_value.is_.return_value.lt.return_value.execute.return_value.data = None
        mock_supabase.table.return_value = mock_table

        with patch("app.tasks.rating_tasks.get_supabase", return_value=mock_supabase):
            from app.tasks.rating_tasks import cleanup_expired_pending_ratings

            result = cleanup_expired_pending_ratings()

        assert result == {"deleted_count": 0}

    @pytest.mark.unit
    def test_retries_on_db_error(self) -> None:
        """Retries the task when a database error occurs."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_table.delete.return_value.is_.return_value.lt.return_value.execute.side_effect = (
            Exception("Connection lost")
        )
        mock_supabase.table.return_value = mock_table

        with patch("app.tasks.rating_tasks.get_supabase", return_value=mock_supabase):
            from app.tasks.rating_tasks import cleanup_expired_pending_ratings

            # The task is bound and should call self.retry()
            # Since we can't easily test Celery retry mechanics in unit tests,
            # we verify that it raises (which triggers retry)
            with pytest.raises(Exception, match="Connection lost"):
                cleanup_expired_pending_ratings()
