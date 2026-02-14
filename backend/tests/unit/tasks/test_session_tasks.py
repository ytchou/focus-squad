"""Unit tests for session phase progression task.

Tests:
- progress_session_phases() with various phase transition scenarios
"""

from unittest.mock import MagicMock, patch

import pytest

from app.models.session import SessionPhase

# =============================================================================
# progress_session_phases() Tests
# =============================================================================


class TestProgressSessionPhases:
    """Tests for the progress_session_phases Celery task."""

    @pytest.mark.unit
    def test_no_active_sessions(self) -> None:
        """Returns early with zero counts when no non-ended sessions exist."""
        mock_supabase = MagicMock()

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.neq.return_value.order.return_value.range.return_value.execute.return_value.data = []

        with (
            patch("app.tasks.session_tasks.get_supabase", return_value=mock_supabase),
            patch("app.tasks.session_tasks.SessionService"),
        ):
            from app.tasks.session_tasks import progress_session_phases

            result = progress_session_phases()

        assert result == {"checked": 0, "progressed": 0}
        mock_table.update.assert_not_called()

    @pytest.mark.unit
    def test_progresses_changed_phase(self) -> None:
        """Updates DB when calculated phase differs from current phase."""
        mock_supabase = MagicMock()

        session_data = {
            "id": "session-1",
            "start_time": "2025-02-07T10:00:00+00:00",
            "current_phase": "setup",
        }

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.neq.return_value.order.return_value.range.return_value.execute.return_value.data = [
            session_data
        ]

        with (
            patch("app.tasks.session_tasks.get_supabase", return_value=mock_supabase),
            patch("app.tasks.session_tasks.SessionService") as MockSessionService,
        ):
            mock_service = MockSessionService.return_value
            mock_service.calculate_current_phase.return_value = SessionPhase.WORK_1

            from app.tasks.session_tasks import progress_session_phases

            result = progress_session_phases()

        assert result == {"checked": 1, "progressed": 1}

        mock_service.calculate_current_phase.assert_called_once_with(session_data)

        mock_table.update.assert_called_once()
        update_args = mock_table.update.call_args.args[0]
        assert update_args["current_phase"] == "work_1"
        assert "phase_started_at" in update_args

    @pytest.mark.unit
    def test_no_progress_when_same_phase(self) -> None:
        """Skips DB update when calculated phase matches current phase."""
        mock_supabase = MagicMock()

        session_data = {
            "id": "session-1",
            "start_time": "2025-02-07T10:00:00+00:00",
            "current_phase": "work_1",
        }

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.neq.return_value.order.return_value.range.return_value.execute.return_value.data = [
            session_data
        ]

        with (
            patch("app.tasks.session_tasks.get_supabase", return_value=mock_supabase),
            patch("app.tasks.session_tasks.SessionService") as MockSessionService,
        ):
            mock_service = MockSessionService.return_value
            mock_service.calculate_current_phase.return_value = SessionPhase.WORK_1

            from app.tasks.session_tasks import progress_session_phases

            result = progress_session_phases()

        assert result == {"checked": 1, "progressed": 0}
        mock_table.update.assert_not_called()

    @pytest.mark.unit
    def test_schedules_cleanup_on_ended_transition(self) -> None:
        """Schedules cleanup_ended_session when phase transitions to ended."""
        mock_supabase = MagicMock()

        session_data = {
            "id": "session-abc",
            "start_time": "2025-02-07T10:00:00+00:00",
            "current_phase": "social",
        }

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.neq.return_value.order.return_value.range.return_value.execute.return_value.data = [
            session_data
        ]

        with (
            patch("app.tasks.session_tasks.get_supabase", return_value=mock_supabase),
            patch("app.tasks.session_tasks.SessionService") as MockSessionService,
            patch("app.tasks.livekit_tasks.cleanup_ended_session") as mock_cleanup,
        ):
            mock_service = MockSessionService.return_value
            mock_service.calculate_current_phase.return_value = SessionPhase.ENDED

            from app.tasks.session_tasks import progress_session_phases

            result = progress_session_phases()

        assert result == {"checked": 1, "progressed": 1}

        mock_cleanup.apply_async.assert_called_once_with(
            args=["session-abc"],
            countdown=60,
        )
