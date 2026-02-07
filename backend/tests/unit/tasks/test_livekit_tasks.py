"""Unit tests for LiveKit tasks (WU1 focus time + cleanup idempotency).

Tests:
- _calculate_focus_minutes() with various scenarios
- cleanup_ended_session idempotency guard
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.tasks.livekit_tasks import _calculate_focus_minutes

# =============================================================================
# _calculate_focus_minutes() Tests (WU1 regression)
# =============================================================================


class TestCalculateFocusMinutes:
    """Tests for focus time calculation logic."""

    @pytest.fixture
    def session(self):
        """Session that started 55 minutes ago."""
        start = (datetime.now(timezone.utc) - timedelta(minutes=55)).isoformat()
        end = datetime.now(timezone.utc).isoformat()
        return {"start_time": start, "end_time": end}

    @pytest.mark.unit
    def test_uses_total_active_minutes_when_available(self, session):
        """Prefers webhook-tracked total_active_minutes over timestamp calc."""
        participant = {"total_active_minutes": 35, "connected_at": None}
        result = _calculate_focus_minutes(participant, session)
        assert result == 35

    @pytest.mark.unit
    def test_caps_active_minutes_at_45(self, session):
        """Caps total_active_minutes at 45 (max work time)."""
        participant = {"total_active_minutes": 60, "connected_at": None}
        result = _calculate_focus_minutes(participant, session)
        assert result == 45

    @pytest.mark.unit
    def test_returns_zero_when_no_data(self, session):
        """Returns 0 when no active minutes and no connected_at."""
        participant = {"total_active_minutes": None, "connected_at": None}
        result = _calculate_focus_minutes(participant, session)
        assert result == 0

    @pytest.mark.unit
    def test_returns_zero_for_zero_active_minutes(self, session):
        """Returns 0 when total_active_minutes is 0."""
        participant = {"total_active_minutes": 0, "connected_at": None}
        result = _calculate_focus_minutes(participant, session)
        assert result == 0

    @pytest.mark.unit
    def test_fallback_calculates_work_phase_overlap(self):
        """When no total_active_minutes, calculates overlap with work phases."""
        start = datetime(2025, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 2, 7, 10, 55, 0, tzinfo=timezone.utc)
        session = {
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        }

        # User connected from minute 0 to minute 55 (full session)
        participant = {
            "total_active_minutes": None,
            "connected_at": start.isoformat(),
            "disconnected_at": end.isoformat(),
        }

        result = _calculate_focus_minutes(participant, session)
        # Work_1: 3-28 min = 25 min, Work_2: 30-50 min = 20 min, Total = 45 min
        assert result == 45

    @pytest.mark.unit
    def test_fallback_partial_session(self):
        """Calculates correct overlap for partial attendance."""
        start = datetime(2025, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 2, 7, 10, 55, 0, tzinfo=timezone.utc)
        session = {
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        }

        # User joined at minute 10 (during work_1) and left at minute 35 (during work_2)
        connected = (start + timedelta(minutes=10)).isoformat()
        disconnected = (start + timedelta(minutes=35)).isoformat()

        participant = {
            "total_active_minutes": None,
            "connected_at": connected,
            "disconnected_at": disconnected,
        }

        result = _calculate_focus_minutes(participant, session)
        # Work_1 overlap: 10-28 min = 18 min
        # Work_2 overlap: 30-35 min = 5 min
        # Total = 23 min
        assert result == 23

    @pytest.mark.unit
    def test_fallback_no_disconnected_uses_end_time(self):
        """Uses session end_time when disconnected_at is None."""
        start = datetime(2025, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 2, 7, 10, 55, 0, tzinfo=timezone.utc)
        session = {
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        }

        # Connected from start, never disconnected
        participant = {
            "total_active_minutes": None,
            "connected_at": start.isoformat(),
            "disconnected_at": None,
        }

        result = _calculate_focus_minutes(participant, session)
        assert result == 45  # Full work overlap

    @pytest.mark.unit
    def test_handles_z_suffix_timestamps(self):
        """Handles timestamps with Z suffix correctly."""
        session = {
            "start_time": "2025-02-07T10:00:00.000Z",
            "end_time": "2025-02-07T10:55:00.000Z",
        }

        participant = {
            "total_active_minutes": None,
            "connected_at": "2025-02-07T10:00:00.000Z",
            "disconnected_at": "2025-02-07T10:55:00.000Z",
        }

        result = _calculate_focus_minutes(participant, session)
        assert result == 45

    @pytest.mark.unit
    def test_no_overlap_when_connected_only_during_break(self):
        """Returns 0 if user was only connected during break phase."""
        start = datetime(2025, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
        session = {
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=55)).isoformat(),
        }

        # Connected only during break (28-30 min)
        connected = (start + timedelta(minutes=28)).isoformat()
        disconnected = (start + timedelta(minutes=30)).isoformat()

        participant = {
            "total_active_minutes": None,
            "connected_at": connected,
            "disconnected_at": disconnected,
        }

        result = _calculate_focus_minutes(participant, session)
        assert result == 0


# =============================================================================
# cleanup_ended_session Idempotency Tests (WU2)
# =============================================================================


class TestCleanupIdempotency:
    """Tests for cleanup_ended_session idempotency guard."""

    @pytest.mark.unit
    def test_skips_already_cleaned_session(self):
        """Returns early if livekit_room_deleted_at is already set."""
        mock_supabase = MagicMock()

        session_data = {
            "id": "session-1",
            "livekit_room_name": "focus-abc",
            "livekit_room_deleted_at": "2025-02-07T10:00:00+00:00",
            "start_time": "2025-02-07T09:00:00+00:00",
        }

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [session_data]
        mock_supabase.table.return_value = mock_table

        with patch("app.tasks.livekit_tasks.get_supabase", return_value=mock_supabase):
            # Import here to avoid Celery task registration issues
            from app.tasks.livekit_tasks import cleanup_ended_session

            result = cleanup_ended_session("session-1")

        assert result["status"] == "already_cleaned_up"
        # Should NOT call update (skip cleanup)
        mock_table.update.assert_not_called()


# =============================================================================
# create_livekit_room Tests
# =============================================================================


class TestCreateLivekitRoom:
    """Tests for create_livekit_room Celery task."""

    @pytest.mark.unit
    def test_creates_room_successfully(self):
        """Creates a LiveKit room and returns room info."""
        mock_supabase = MagicMock()

        session_data = {
            "id": "session-1",
            "livekit_room_name": "focus-abc",
            "mode": "forced_audio",
        }

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [session_data]
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value = mock_table

        room_info = {"name": "focus-abc", "sid": "room-123"}

        with (
            patch("app.tasks.livekit_tasks.get_supabase", return_value=mock_supabase),
            patch("app.tasks.livekit_tasks.LiveKitService"),
            patch("app.tasks.livekit_tasks.run_async", return_value=room_info),
        ):
            from app.tasks.livekit_tasks import create_livekit_room

            result = create_livekit_room("session-1")

        assert result == room_info

    @pytest.mark.unit
    def test_session_not_found(self):
        """Returns error dict when session does not exist."""
        mock_supabase = MagicMock()

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []
        mock_supabase.table.return_value = mock_table

        with patch("app.tasks.livekit_tasks.get_supabase", return_value=mock_supabase):
            from app.tasks.livekit_tasks import create_livekit_room

            result = create_livekit_room("nonexistent")

        assert result == {"error": "Session not found"}

    @pytest.mark.unit
    def test_updates_room_created_timestamp(self):
        """Verifies livekit_room_created_at is updated after room creation."""
        mock_supabase = MagicMock()

        session_data = {
            "id": "session-1",
            "livekit_room_name": "focus-abc",
            "mode": "forced_audio",
        }

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [session_data]
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value = mock_table

        with (
            patch("app.tasks.livekit_tasks.get_supabase", return_value=mock_supabase),
            patch("app.tasks.livekit_tasks.LiveKitService"),
            patch(
                "app.tasks.livekit_tasks.run_async",
                return_value={"name": "focus-abc", "sid": "room-123"},
            ),
        ):
            from app.tasks.livekit_tasks import create_livekit_room

            create_livekit_room("session-1")

        mock_table.update.assert_called_once_with({"livekit_room_created_at": "now()"})


# =============================================================================
# cleanup_ended_session Full Flow Tests
# =============================================================================


class TestCleanupEndedSessionFull:
    """Tests for cleanup_ended_session full cleanup flow."""

    @pytest.mark.unit
    def test_full_cleanup_flow(self):
        """Full cleanup: deletes room, updates stats, awards referrals."""
        mock_supabase = MagicMock()

        session_data = {
            "id": "session-1",
            "livekit_room_name": "focus-abc",
            "livekit_room_deleted_at": None,
            "start_time": "2025-02-07T10:00:00+00:00",
        }

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [session_data]
        mock_table.update.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value = mock_table

        with (
            patch("app.tasks.livekit_tasks.get_supabase", return_value=mock_supabase),
            patch("app.tasks.livekit_tasks.LiveKitService"),
            patch("app.tasks.livekit_tasks.run_async", return_value=True),
            patch(
                "app.tasks.livekit_tasks._update_user_session_stats", return_value=2
            ) as mock_stats,
            patch(
                "app.tasks.livekit_tasks._award_referral_bonuses", return_value=1
            ) as mock_referrals,
        ):
            from app.tasks.livekit_tasks import cleanup_ended_session

            result = cleanup_ended_session("session-1")

        assert result["status"] == "cleaned_up"
        assert result["room_name"] == "focus-abc"
        assert result["stats_updated"] == 2
        assert result["referrals_awarded"] == 1
        mock_table.update.assert_called_once_with({"livekit_room_deleted_at": "now()"})
        mock_stats.assert_called_once_with(mock_supabase, "session-1", session_data)
        mock_referrals.assert_called_once_with(mock_supabase, "session-1", session_data)

    @pytest.mark.unit
    def test_session_not_found(self):
        """Returns session_not_found when session does not exist."""
        mock_supabase = MagicMock()

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []
        mock_supabase.table.return_value = mock_table

        with patch("app.tasks.livekit_tasks.get_supabase", return_value=mock_supabase):
            from app.tasks.livekit_tasks import cleanup_ended_session

            result = cleanup_ended_session("nonexistent")

        assert result == {"status": "session_not_found"}


# =============================================================================
# fill_empty_seats_with_ai Tests
# =============================================================================


class TestFillEmptySeatsWithAI:
    """Tests for fill_empty_seats_with_ai Celery task."""

    @pytest.mark.unit
    def test_fills_remaining_seats(self):
        """Fills remaining seats with AI companions when under 4."""
        mock_supabase = MagicMock()

        # 2 existing participants
        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = [
            {"id": "p1"},
            {"id": "p2"},
        ]
        mock_supabase.table.return_value = mock_table

        mock_session_service = MagicMock()
        mock_session_service.add_ai_companions.return_value = [
            {"id": "ai-1"},
            {"id": "ai-2"},
        ]

        with (
            patch("app.tasks.livekit_tasks.get_supabase", return_value=mock_supabase),
            patch(
                "app.services.session_service.SessionService",
                return_value=mock_session_service,
            ),
        ):
            from app.tasks.livekit_tasks import fill_empty_seats_with_ai

            result = fill_empty_seats_with_ai("session-1")

        assert result == {"ai_companions_added": 2}
        mock_session_service.add_ai_companions.assert_called_once_with("session-1", 2)

    @pytest.mark.unit
    def test_no_fill_when_full(self):
        """Does not add AI companions when table is already full."""
        mock_supabase = MagicMock()

        # 4 existing participants (full table)
        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = [
            {"id": "p1"},
            {"id": "p2"},
            {"id": "p3"},
            {"id": "p4"},
        ]
        mock_supabase.table.return_value = mock_table

        with patch("app.tasks.livekit_tasks.get_supabase", return_value=mock_supabase):
            from app.tasks.livekit_tasks import fill_empty_seats_with_ai

            result = fill_empty_seats_with_ai("session-1")

        assert result == {"ai_companions_added": 0}


# =============================================================================
# _update_user_session_stats Tests
# =============================================================================


class TestUpdateUserSessionStats:
    """Tests for _update_user_session_stats helper function."""

    @pytest.mark.unit
    def test_updates_stats_for_completing_participants(self):
        """Updates stats for participants who completed the session."""
        mock_supabase = MagicMock()

        # 2 participants, both human
        participants_data = [
            {
                "user_id": "user-1",
                "left_at": None,
                "total_active_minutes": 40,
                "connected_at": "2025-02-07T10:00:00+00:00",
                "disconnected_at": "2025-02-07T10:55:00+00:00",
            },
            {
                "user_id": "user-2",
                "left_at": "2025-02-07T10:10:00+00:00",
                "total_active_minutes": 5,
                "connected_at": "2025-02-07T10:00:00+00:00",
                "disconnected_at": "2025-02-07T10:10:00+00:00",
            },
        ]

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
            participants_data
        )
        mock_supabase.table.return_value = mock_table

        session = {
            "start_time": "2025-02-07T10:00:00+00:00",
            "end_time": "2025-02-07T10:55:00+00:00",
        }

        mock_user_service = MagicMock()

        # Only user-1 completed the session
        def is_completed_side_effect(participant, session_start):
            return participant.get("user_id") == "user-1"

        with (
            patch(
                "app.routers.webhooks.is_session_completed",
                side_effect=is_completed_side_effect,
            ),
            patch(
                "app.routers.webhooks._parse_session_start_time",
                return_value=datetime(2025, 2, 7, 10, 0, 0, tzinfo=timezone.utc),
            ),
            patch("app.services.user_service.UserService", return_value=mock_user_service),
        ):
            from app.tasks.livekit_tasks import _update_user_session_stats

            result = _update_user_session_stats(mock_supabase, "session-1", session)

        assert result == 1
        mock_user_service.record_session_completion.assert_called_once()

    @pytest.mark.unit
    def test_returns_zero_when_no_participants(self):
        """Returns 0 when there are no participants."""
        mock_supabase = MagicMock()

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        mock_supabase.table.return_value = mock_table

        session = {
            "start_time": "2025-02-07T10:00:00+00:00",
            "end_time": "2025-02-07T10:55:00+00:00",
        }

        from app.tasks.livekit_tasks import _update_user_session_stats

        result = _update_user_session_stats(mock_supabase, "session-1", session)

        assert result == 0


# =============================================================================
# _award_referral_bonuses Tests
# =============================================================================


class TestAwardReferralBonusesTask:
    """Tests for _award_referral_bonuses helper function."""

    @pytest.mark.unit
    def test_awards_bonus_for_completing_user(self):
        """Awards referral bonus for a user who completed the session."""
        mock_supabase = MagicMock()

        participants_data = [
            {
                "user_id": "user-1",
                "left_at": None,
                "total_active_minutes": 40,
            },
        ]

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
            participants_data
        )
        mock_supabase.table.return_value = mock_table

        session = {"start_time": "2025-02-07T10:00:00+00:00"}

        mock_credit_service = MagicMock()
        mock_credit_service.award_referral_bonus.return_value = True

        with (
            patch("app.routers.webhooks.is_session_completed", return_value=True),
            patch(
                "app.routers.webhooks._parse_session_start_time",
                return_value=datetime(2025, 2, 7, 10, 0, 0, tzinfo=timezone.utc),
            ),
            patch(
                "app.tasks.livekit_tasks.CreditService",
                return_value=mock_credit_service,
            ),
        ):
            from app.tasks.livekit_tasks import _award_referral_bonuses

            result = _award_referral_bonuses(mock_supabase, "session-1", session)

        assert result == 1
        mock_credit_service.award_referral_bonus.assert_called_once_with("user-1")

    @pytest.mark.unit
    def test_returns_zero_no_participants(self):
        """Returns 0 when there are no participants."""
        mock_supabase = MagicMock()

        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        mock_supabase.table.return_value = mock_table

        session = {"start_time": "2025-02-07T10:00:00+00:00"}

        from app.tasks.livekit_tasks import _award_referral_bonuses

        result = _award_referral_bonuses(mock_supabase, "session-1", session)

        assert result == 0


# =============================================================================
# log_livekit_event Tests
# =============================================================================


class TestLogLivekitEvent:
    """Tests for log_livekit_event Celery task."""

    @pytest.mark.unit
    def test_logs_without_error(self):
        """Calling log_livekit_event should not raise any exceptions."""
        from app.tasks.livekit_tasks import log_livekit_event

        log_livekit_event("test_event", {"key": "val"})
