"""Unit tests for schedule tasks (create_scheduled_sessions).

Tests the Celery task that auto-creates private sessions from recurring schedules.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.tasks.schedule_tasks import create_scheduled_sessions


class TestCreateScheduledSessions:
    """Tests for the create_scheduled_sessions Celery task."""

    @pytest.mark.unit
    def test_returns_summary_dict(self) -> None:
        """Task returns dict with sessions_created and invitations_sent."""
        mock_service = MagicMock()
        mock_service.create_scheduled_sessions.return_value = {
            "sessions_created": 2,
            "invitations_sent": 4,
        }

        with patch(
            "app.tasks.schedule_tasks.ScheduleService",
            return_value=mock_service,
        ):
            result = create_scheduled_sessions()

        assert result == {"sessions_created": 2, "invitations_sent": 4}

    @pytest.mark.unit
    def test_calls_schedule_service(self) -> None:
        """Task delegates work to ScheduleService."""
        mock_service = MagicMock()
        mock_service.create_scheduled_sessions.return_value = {
            "sessions_created": 0,
            "invitations_sent": 0,
        }

        with patch(
            "app.tasks.schedule_tasks.ScheduleService",
            return_value=mock_service,
        ):
            create_scheduled_sessions()

        mock_service.create_scheduled_sessions.assert_called_once()

    @pytest.mark.unit
    def test_logs_completion(self) -> None:
        """Task logs completion with counts."""
        mock_service = MagicMock()
        mock_service.create_scheduled_sessions.return_value = {
            "sessions_created": 1,
            "invitations_sent": 3,
        }

        with (
            patch(
                "app.tasks.schedule_tasks.ScheduleService",
                return_value=mock_service,
            ),
            patch("app.tasks.schedule_tasks.logger") as mock_logger,
        ):
            create_scheduled_sessions()

            mock_logger.info.assert_called_once()

    @pytest.mark.unit
    def test_handles_zero_schedules(self) -> None:
        """Task handles case with no schedules gracefully."""
        mock_service = MagicMock()
        mock_service.create_scheduled_sessions.return_value = {
            "sessions_created": 0,
            "invitations_sent": 0,
        }

        with patch(
            "app.tasks.schedule_tasks.ScheduleService",
            return_value=mock_service,
        ):
            result = create_scheduled_sessions()

        assert result["sessions_created"] == 0
        assert result["invitations_sent"] == 0

    @pytest.mark.unit
    def test_propagates_service_exception(self) -> None:
        """Task propagates exceptions from ScheduleService."""
        mock_service = MagicMock()
        mock_service.create_scheduled_sessions.side_effect = Exception("DB error")

        with patch(
            "app.tasks.schedule_tasks.ScheduleService",
            return_value=mock_service,
        ):
            with pytest.raises(Exception) as exc_info:
                create_scheduled_sessions()

            assert "DB error" in str(exc_info.value)

    @pytest.mark.unit
    def test_creates_new_service_instance(self) -> None:
        """Task creates a fresh ScheduleService instance each call."""
        mock_service_class = MagicMock()
        mock_service_class.return_value.create_scheduled_sessions.return_value = {
            "sessions_created": 0,
            "invitations_sent": 0,
        }

        with patch(
            "app.tasks.schedule_tasks.ScheduleService",
            mock_service_class,
        ):
            create_scheduled_sessions()
            create_scheduled_sessions()

        assert mock_service_class.call_count == 2
