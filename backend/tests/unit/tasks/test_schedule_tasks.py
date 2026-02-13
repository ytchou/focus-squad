"""Unit tests for schedule tasks (create_scheduled_sessions).

Tests the Celery task that auto-creates private sessions from recurring schedules.
"""

import importlib
from unittest.mock import MagicMock, patch

import pytest


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
            "app.services.schedule_service.ScheduleService",
            return_value=mock_service,
        ):
            # Re-import to get fresh function that uses our mock
            import app.tasks.schedule_tasks as schedule_tasks_module

            importlib.reload(schedule_tasks_module)
            result = schedule_tasks_module.create_scheduled_sessions()

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
            "app.services.schedule_service.ScheduleService",
            return_value=mock_service,
        ):
            import app.tasks.schedule_tasks as schedule_tasks_module

            importlib.reload(schedule_tasks_module)
            schedule_tasks_module.create_scheduled_sessions()

        mock_service.create_scheduled_sessions.assert_called_once()

    @pytest.mark.unit
    def test_logs_completion(self) -> None:
        """Task logs completion with counts."""
        mock_service = MagicMock()
        mock_service.create_scheduled_sessions.return_value = {
            "sessions_created": 1,
            "invitations_sent": 3,
        }

        with patch(
            "app.services.schedule_service.ScheduleService",
            return_value=mock_service,
        ):
            import app.tasks.schedule_tasks as schedule_tasks_module

            importlib.reload(schedule_tasks_module)

            # Patch logger after reload so we capture actual logger reference
            with patch.object(schedule_tasks_module, "logger") as mock_logger:
                schedule_tasks_module.create_scheduled_sessions()

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
            "app.services.schedule_service.ScheduleService",
            return_value=mock_service,
        ):
            import app.tasks.schedule_tasks as schedule_tasks_module

            importlib.reload(schedule_tasks_module)
            result = schedule_tasks_module.create_scheduled_sessions()

        assert result["sessions_created"] == 0
        assert result["invitations_sent"] == 0

    @pytest.mark.unit
    def test_propagates_service_exception(self) -> None:
        """Task propagates exceptions from ScheduleService."""
        mock_service = MagicMock()
        mock_service.create_scheduled_sessions.side_effect = Exception("DB error")

        with patch(
            "app.services.schedule_service.ScheduleService",
            return_value=mock_service,
        ):
            import app.tasks.schedule_tasks as schedule_tasks_module

            importlib.reload(schedule_tasks_module)

            with pytest.raises(Exception) as exc_info:
                schedule_tasks_module.create_scheduled_sessions()

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
            "app.services.schedule_service.ScheduleService", mock_service_class
        ):
            import app.tasks.schedule_tasks as schedule_tasks_module

            importlib.reload(schedule_tasks_module)
            schedule_tasks_module.create_scheduled_sessions()
            schedule_tasks_module.create_scheduled_sessions()

        assert mock_service_class.call_count == 2
