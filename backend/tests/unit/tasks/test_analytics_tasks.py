from unittest.mock import MagicMock, patch

import pytest


class TestCleanupOldAnalytics:
    """Tests for analytics cleanup Celery task."""

    @patch("app.tasks.analytics_tasks.get_supabase")
    def test_cleanup_single_batch(self, mock_get_supabase: MagicMock):
        """Should delete all old events in one batch if fewer than batch_size."""
        from app.tasks.analytics_tasks import cleanup_old_analytics

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # First call returns 500 deleted (less than 1000 batch)
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={"deleted": 500})

        result = cleanup_old_analytics()

        assert result == {"deleted": 500}
        mock_supabase.rpc.assert_called_once_with(
            "delete_old_analytics", {"cutoff_interval": "1 year", "batch_limit": 1000}
        )

    @patch("app.tasks.analytics_tasks.get_supabase")
    def test_cleanup_multiple_batches(self, mock_get_supabase: MagicMock):
        """Should loop until fewer than batch_size deleted."""
        from app.tasks.analytics_tasks import cleanup_old_analytics

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # First two calls return 1000, third returns 200
        mock_supabase.rpc.return_value.execute.side_effect = [
            MagicMock(data={"deleted": 1000}),
            MagicMock(data={"deleted": 1000}),
            MagicMock(data={"deleted": 200}),
        ]

        result = cleanup_old_analytics()

        assert result == {"deleted": 2200}  # 1000 + 1000 + 200
        assert mock_supabase.rpc.call_count == 3

    @patch("app.tasks.analytics_tasks.get_supabase")
    def test_cleanup_nothing_to_delete(self, mock_get_supabase: MagicMock):
        """Should return 0 when no old events exist."""
        from app.tasks.analytics_tasks import cleanup_old_analytics

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(data={"deleted": 0})

        result = cleanup_old_analytics()

        assert result == {"deleted": 0}

    @patch("app.tasks.analytics_tasks.get_supabase")
    def test_retries_on_rpc_error(self, mock_get_supabase: MagicMock):
        """Should trigger retry when RPC call fails."""
        from app.tasks.analytics_tasks import cleanup_old_analytics

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.rpc.return_value.execute.side_effect = Exception("RPC failed")

        # The task is bound and should call self.retry()
        # Since we can't easily test Celery retry mechanics in unit tests,
        # we verify that it raises (which triggers retry)
        with pytest.raises(Exception, match="RPC failed"):
            cleanup_old_analytics()
