"""Unit tests for ScheduleService."""

from datetime import datetime, time, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.constants import MAX_RECURRING_SCHEDULES, SESSION_DURATION_MINUTES
from app.models.schedule import (
    RecurringScheduleCreate,
    RecurringScheduleUpdate,
    ScheduleLimitError,
    ScheduleNotFoundError,
    ScheduleOwnershipError,
    SchedulePermissionError,
)
from app.services.schedule_service import ScheduleService

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_supabase():
    """Mock Supabase client with table-specific routing."""
    mock = MagicMock()

    credits_mock = MagicMock()
    partnerships_mock = MagicMock()
    recurring_schedules_mock = MagicMock()
    sessions_mock = MagicMock()
    session_participants_mock = MagicMock()
    table_invitations_mock = MagicMock()
    users_mock = MagicMock()

    def table_router(name):
        routes = {
            "credits": credits_mock,
            "partnerships": partnerships_mock,
            "recurring_schedules": recurring_schedules_mock,
            "sessions": sessions_mock,
            "session_participants": session_participants_mock,
            "table_invitations": table_invitations_mock,
            "users": users_mock,
        }
        return routes.get(name, MagicMock())

    mock.table.side_effect = table_router
    return (
        mock,
        credits_mock,
        partnerships_mock,
        recurring_schedules_mock,
        sessions_mock,
        session_participants_mock,
        table_invitations_mock,
        users_mock,
    )


@pytest.fixture
def schedule_service(mock_supabase):
    """ScheduleService with mocked Supabase."""
    mock, *_ = mock_supabase
    return ScheduleService(supabase=mock)


@pytest.fixture
def sample_schedule_row():
    """Sample recurring schedule DB row."""
    return {
        "id": "sched-001",
        "creator_id": "user-creator",
        "partner_ids": ["user-partner-1"],
        "days_of_week": [1, 3, 5],
        "slot_time": "09:00:00",
        "timezone": "Asia/Taipei",
        "label": "Morning focus",
        "table_mode": "forced_audio",
        "max_seats": 4,
        "fill_ai": True,
        "topic": "Deep work",
        "is_active": True,
        "created_at": "2026-01-15T08:00:00+00:00",
    }


@pytest.fixture
def sample_create_data():
    """Sample RecurringScheduleCreate payload."""
    return RecurringScheduleCreate(
        partner_ids=["user-partner-1"],
        days_of_week=[1, 3, 5],
        slot_time=time(9, 0),
        timezone="Asia/Taipei",
        label="Morning focus",
        table_mode="forced_audio",
        max_seats=4,
        fill_ai=True,
        topic="Deep work",
    )


# =============================================================================
# create_schedule
# =============================================================================


class TestCreateSchedule:
    """Tests for create_schedule() method."""

    @pytest.mark.unit
    def test_create_schedule_success(
        self, schedule_service, mock_supabase, sample_schedule_row, sample_create_data
    ) -> None:
        """Creates schedule when user is infinite tier, valid partners, under limit."""
        (
            _mock,
            credits_mock,
            partnerships_mock,
            recurring_schedules_mock,
            _sessions,
            _participants,
            _invitations,
            users_mock,
        ) = mock_supabase

        # Tier validation: infinite tier
        credits_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"tier": "infinite"}
        ]

        # Partner validation: _validate_partners calls partnerships table twice
        # (once as requester, once as addressee). Use side_effect to return
        # different results for each call.
        requester_result = MagicMock()
        requester_result.data = [{"addressee_id": "user-partner-1"}]
        addressee_result = MagicMock()
        addressee_result.data = []
        partnerships_mock.select.return_value.eq.return_value.eq.return_value.in_.return_value.execute.side_effect = [
            requester_result,
            addressee_result,
        ]

        # Count existing schedules: under limit
        count_result = MagicMock()
        count_result.count = 2
        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value = (
            count_result
        )

        # Insert succeeds
        recurring_schedules_mock.insert.return_value.execute.return_value.data = [
            sample_schedule_row
        ]

        # Resolve partner names
        users_mock.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "user-partner-1", "display_name": "Alice", "username": "alice"}
        ]

        result = schedule_service.create_schedule("user-creator", sample_create_data)

        assert result["id"] == "sched-001"
        assert result["creator_id"] == "user-creator"
        assert result["partner_ids"] == ["user-partner-1"]
        assert result["partner_names"] == ["Alice"]
        assert result["slot_time"] == "09:00"
        assert result["days_of_week"] == [1, 3, 5]
        assert result["label"] == "Morning focus"
        assert result["table_mode"] == "forced_audio"
        assert result["is_active"] is True

    @pytest.mark.unit
    def test_create_schedule_non_infinite_tier(
        self, schedule_service, mock_supabase, sample_create_data
    ) -> None:
        """Raises SchedulePermissionError when user is not on infinite tier."""
        _mock, credits_mock, *_ = mock_supabase

        # Tier validation: pro tier (not infinite)
        credits_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"tier": "pro"}
        ]

        with pytest.raises(SchedulePermissionError, match="Unlimited plan"):
            schedule_service.create_schedule("user-123", sample_create_data)

    @pytest.mark.unit
    def test_create_schedule_no_credit_record(
        self, schedule_service, mock_supabase, sample_create_data
    ) -> None:
        """Raises SchedulePermissionError when user has no credit record."""
        _mock, credits_mock, *_ = mock_supabase

        credits_mock.select.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(SchedulePermissionError, match="No credit record"):
            schedule_service.create_schedule("user-123", sample_create_data)

    @pytest.mark.unit
    def test_create_schedule_non_partner(
        self, schedule_service, mock_supabase, sample_create_data
    ) -> None:
        """Raises SchedulePermissionError when partner_id is not an accepted partner."""
        (
            _mock,
            credits_mock,
            partnerships_mock,
            *_rest,
        ) = mock_supabase

        # Tier validation: infinite
        credits_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"tier": "infinite"}
        ]

        # Partner validation: both queries return empty (no accepted partnership)
        requester_result = MagicMock()
        requester_result.data = []
        addressee_result = MagicMock()
        addressee_result.data = []
        partnerships_mock.select.return_value.eq.return_value.eq.return_value.in_.return_value.execute.side_effect = [
            requester_result,
            addressee_result,
        ]

        with pytest.raises(SchedulePermissionError, match="Not all partner_ids"):
            schedule_service.create_schedule("user-creator", sample_create_data)

    @pytest.mark.unit
    def test_create_schedule_limit_exceeded(
        self, schedule_service, mock_supabase, sample_create_data
    ) -> None:
        """Raises ScheduleLimitError when at MAX_RECURRING_SCHEDULES."""
        (
            _mock,
            credits_mock,
            partnerships_mock,
            recurring_schedules_mock,
            *_rest,
        ) = mock_supabase

        # Tier validation: infinite
        credits_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"tier": "infinite"}
        ]

        # Partner validation passes
        requester_result = MagicMock()
        requester_result.data = [{"addressee_id": "user-partner-1"}]
        addressee_result = MagicMock()
        addressee_result.data = []
        partnerships_mock.select.return_value.eq.return_value.eq.return_value.in_.return_value.execute.side_effect = [
            requester_result,
            addressee_result,
        ]

        # Count existing schedules: at limit
        count_result = MagicMock()
        count_result.count = MAX_RECURRING_SCHEDULES
        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value = (
            count_result
        )

        with pytest.raises(ScheduleLimitError, match=str(MAX_RECURRING_SCHEDULES)):
            schedule_service.create_schedule("user-creator", sample_create_data)


# =============================================================================
# list_schedules
# =============================================================================


class TestListSchedules:
    """Tests for list_schedules() method."""

    @pytest.mark.unit
    def test_list_schedules_returns_data(
        self, schedule_service, mock_supabase, sample_schedule_row
    ) -> None:
        """Returns schedules with partner names resolved."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            _sessions,
            _participants,
            _invitations,
            users_mock,
        ) = mock_supabase

        # List query returns two schedules
        second_schedule = {
            **sample_schedule_row,
            "id": "sched-002",
            "partner_ids": ["user-partner-2"],
            "label": "Evening study",
            "slot_time": "20:00:00",
        }
        recurring_schedules_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            sample_schedule_row,
            second_schedule,
        ]

        # Resolve partner names (called per schedule)
        users_mock.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "user-partner-1", "display_name": "Alice", "username": "alice"},
            {"id": "user-partner-2", "display_name": None, "username": "bob"},
        ]

        result = schedule_service.list_schedules("user-creator")

        assert len(result) == 2
        assert result[0]["id"] == "sched-001"
        assert result[0]["slot_time"] == "09:00"
        assert result[1]["id"] == "sched-002"
        assert result[1]["slot_time"] == "20:00"

    @pytest.mark.unit
    def test_list_schedules_empty(self, schedule_service, mock_supabase) -> None:
        """Returns empty list when user has no schedules."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            *_rest,
        ) = mock_supabase

        recurring_schedules_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

        result = schedule_service.list_schedules("user-no-schedules")

        assert result == []


# =============================================================================
# update_schedule
# =============================================================================


class TestUpdateSchedule:
    """Tests for update_schedule() method."""

    @pytest.mark.unit
    def test_update_schedule_success(
        self, schedule_service, mock_supabase, sample_schedule_row
    ) -> None:
        """Partial update works and returns updated schedule info."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            _sessions,
            _participants,
            _invitations,
            users_mock,
        ) = mock_supabase

        # Fetch existing schedule
        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = [
            sample_schedule_row
        ]

        # Update succeeds
        updated_row = {**sample_schedule_row, "label": "Updated label", "fill_ai": False}
        recurring_schedules_mock.update.return_value.eq.return_value.execute.return_value.data = [
            updated_row
        ]

        # Resolve partner names
        users_mock.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "user-partner-1", "display_name": "Alice", "username": "alice"}
        ]

        update_data = RecurringScheduleUpdate(label="Updated label", fill_ai=False)
        result = schedule_service.update_schedule("sched-001", "user-creator", update_data)

        assert result["label"] == "Updated label"
        assert result["fill_ai"] is False

    @pytest.mark.unit
    def test_update_schedule_not_found(self, schedule_service, mock_supabase) -> None:
        """Raises ScheduleNotFoundError when schedule does not exist."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            *_rest,
        ) = mock_supabase

        # Fetch returns empty
        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = []

        update_data = RecurringScheduleUpdate(label="New label")
        with pytest.raises(ScheduleNotFoundError, match="not found"):
            schedule_service.update_schedule("nonexistent-id", "user-creator", update_data)

    @pytest.mark.unit
    def test_update_schedule_wrong_owner(
        self, schedule_service, mock_supabase, sample_schedule_row
    ) -> None:
        """Raises ScheduleOwnershipError when user is not the creator."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            *_rest,
        ) = mock_supabase

        # Fetch returns schedule owned by user-creator
        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = [
            sample_schedule_row
        ]

        update_data = RecurringScheduleUpdate(label="Hijacked")
        with pytest.raises(ScheduleOwnershipError, match="not the creator"):
            schedule_service.update_schedule("sched-001", "user-impostor", update_data)

    @pytest.mark.unit
    def test_update_schedule_no_changes(
        self, schedule_service, mock_supabase, sample_schedule_row
    ) -> None:
        """Returns current schedule when no fields are set in update payload."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            _sessions,
            _participants,
            _invitations,
            users_mock,
        ) = mock_supabase

        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = [
            sample_schedule_row
        ]

        # Resolve partner names (called via _schedule_to_info)
        users_mock.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "user-partner-1", "display_name": "Alice", "username": "alice"}
        ]

        update_data = RecurringScheduleUpdate()  # All None
        result = schedule_service.update_schedule("sched-001", "user-creator", update_data)

        # Should return existing schedule without calling update
        assert result["id"] == "sched-001"
        recurring_schedules_mock.update.assert_not_called()

    @pytest.mark.unit
    def test_update_schedule_validates_new_partners(
        self, schedule_service, mock_supabase, sample_schedule_row
    ) -> None:
        """Validates partner_ids when they are changed in the update."""
        (
            _mock,
            _credits,
            partnerships_mock,
            recurring_schedules_mock,
            *_rest,
        ) = mock_supabase

        # Fetch existing schedule
        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = [
            sample_schedule_row
        ]

        # Partner validation: new partner not accepted (both queries return empty)
        requester_result = MagicMock()
        requester_result.data = []
        addressee_result = MagicMock()
        addressee_result.data = []
        partnerships_mock.select.return_value.eq.return_value.eq.return_value.in_.return_value.execute.side_effect = [
            requester_result,
            addressee_result,
        ]

        update_data = RecurringScheduleUpdate(partner_ids=["user-stranger"])
        with pytest.raises(SchedulePermissionError, match="Not all partner_ids"):
            schedule_service.update_schedule("sched-001", "user-creator", update_data)


# =============================================================================
# delete_schedule
# =============================================================================


class TestDeleteSchedule:
    """Tests for delete_schedule() method."""

    @pytest.mark.unit
    def test_delete_schedule_success(self, schedule_service, mock_supabase) -> None:
        """Deletes the schedule successfully."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            *_rest,
        ) = mock_supabase

        # Fetch returns schedule owned by user-creator
        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "sched-001", "creator_id": "user-creator"}
        ]

        # Delete chain
        recurring_schedules_mock.delete.return_value.eq.return_value.execute.return_value.data = []

        schedule_service.delete_schedule("sched-001", "user-creator")

        # Verify delete was called
        recurring_schedules_mock.delete.assert_called_once()

    @pytest.mark.unit
    def test_delete_schedule_not_found(self, schedule_service, mock_supabase) -> None:
        """Raises ScheduleNotFoundError when schedule does not exist."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            *_rest,
        ) = mock_supabase

        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(ScheduleNotFoundError, match="not found"):
            schedule_service.delete_schedule("nonexistent-id", "user-creator")

    @pytest.mark.unit
    def test_delete_schedule_wrong_owner(self, schedule_service, mock_supabase) -> None:
        """Raises ScheduleOwnershipError when user is not the creator."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            *_rest,
        ) = mock_supabase

        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "sched-001", "creator_id": "user-creator"}
        ]

        with pytest.raises(ScheduleOwnershipError, match="not the creator"):
            schedule_service.delete_schedule("sched-001", "user-impostor")


# =============================================================================
# create_scheduled_sessions
# =============================================================================


class TestCreateScheduledSessions:
    """Tests for create_scheduled_sessions() method."""

    @pytest.mark.unit
    @patch("app.services.schedule_service.datetime")
    def test_creates_session_when_day_matches(
        self, mock_datetime, schedule_service, mock_supabase
    ) -> None:
        """Creates session when today's weekday matches the schedule's days_of_week."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            sessions_mock,
            session_participants_mock,
            table_invitations_mock,
            users_mock,
        ) = mock_supabase

        # Fix "now" to Wednesday 2026-02-11 06:00 UTC
        # In Asia/Taipei (UTC+8), that's Wednesday 14:00
        # Wednesday isoweekday()=3, %7=3 -> day_of_week=3
        fixed_now = datetime(2026, 2, 11, 6, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        # Allow timedelta and other datetime operations to work normally
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_datetime.combine = datetime.combine
        mock_datetime.fromisoformat = datetime.fromisoformat

        schedule_row = {
            "id": "sched-wed",
            "creator_id": "user-creator",
            "partner_ids": ["user-partner-1"],
            "days_of_week": [3],  # Wednesday (isoweekday 3 % 7 = 3)
            "slot_time": "15:00:00",  # 15:00 Taipei = 07:00 UTC
            "timezone": "Asia/Taipei",
            "table_mode": "forced_audio",
            "topic": "Focus time",
            "max_seats": 4,
            "fill_ai": True,
            "is_active": True,
        }

        # Fetch active schedules
        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = [
            schedule_row
        ]

        # No existing session for this schedule + time
        sessions_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        # Session insert succeeds
        sessions_mock.insert.return_value.execute.return_value.data = [{"id": "session-new-1"}]

        # Participant insert succeeds
        session_participants_mock.insert.return_value.execute.return_value.data = [{}]

        # Partner not banned
        users_mock.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "user-partner-1", "banned_until": None}
        ]

        # Invitation insert succeeds
        table_invitations_mock.insert.return_value.execute.return_value.data = [{}]

        result = schedule_service.create_scheduled_sessions(lookahead_hours=24)

        assert result["sessions_created"] == 1
        assert result["invitations_sent"] == 1

        # Verify session was inserted with correct data
        session_insert_call = sessions_mock.insert.call_args.args[0]
        assert session_insert_call["is_private"] is True
        assert session_insert_call["created_by"] == "user-creator"
        assert session_insert_call["recurring_schedule_id"] == "sched-wed"
        assert session_insert_call["mode"] == "forced_audio"
        assert session_insert_call["max_seats"] == 4

        # Verify creator was added as participant at seat 1
        participant_insert_call = session_participants_mock.insert.call_args.args[0]
        assert participant_insert_call["user_id"] == "user-creator"
        assert participant_insert_call["seat_number"] == 1
        assert participant_insert_call["participant_type"] == "human"

    @pytest.mark.unit
    @patch("app.services.schedule_service.datetime")
    def test_skip_wrong_day(self, mock_datetime, schedule_service, mock_supabase) -> None:
        """Skips session creation when today does not match days_of_week."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            sessions_mock,
            *_rest,
        ) = mock_supabase

        # Fix "now" to Wednesday 2026-02-11 06:00 UTC
        fixed_now = datetime(2026, 2, 11, 6, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_datetime.combine = datetime.combine
        mock_datetime.fromisoformat = datetime.fromisoformat

        schedule_row = {
            "id": "sched-mon",
            "creator_id": "user-creator",
            "partner_ids": [],
            "days_of_week": [1],  # Monday only (Wed isoweekday=3, %7=3, not 1)
            "slot_time": "09:00:00",
            "timezone": "Asia/Taipei",
            "table_mode": "quiet",
            "topic": None,
            "max_seats": 2,
            "fill_ai": False,
            "is_active": True,
        }

        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = [
            schedule_row
        ]

        result = schedule_service.create_scheduled_sessions(lookahead_hours=24)

        assert result["sessions_created"] == 0
        assert result["invitations_sent"] == 0
        sessions_mock.insert.assert_not_called()

    @pytest.mark.unit
    @patch("app.services.schedule_service.datetime")
    def test_skip_existing_session(self, mock_datetime, schedule_service, mock_supabase) -> None:
        """Skips when a session already exists for this schedule + start_time."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            sessions_mock,
            *_rest,
        ) = mock_supabase

        # Fix "now" to Wednesday 2026-02-11 06:00 UTC
        fixed_now = datetime(2026, 2, 11, 6, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_datetime.combine = datetime.combine
        mock_datetime.fromisoformat = datetime.fromisoformat

        schedule_row = {
            "id": "sched-wed",
            "creator_id": "user-creator",
            "partner_ids": [],
            "days_of_week": [3],  # Wednesday matches
            "slot_time": "15:00:00",
            "timezone": "Asia/Taipei",
            "table_mode": "forced_audio",
            "topic": None,
            "max_seats": 4,
            "fill_ai": True,
            "is_active": True,
        }

        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = [
            schedule_row
        ]

        # Existing session found for this schedule + start_time
        sessions_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-already-exists"}
        ]

        result = schedule_service.create_scheduled_sessions(lookahead_hours=24)

        assert result["sessions_created"] == 0
        assert result["invitations_sent"] == 0
        sessions_mock.insert.assert_not_called()

    @pytest.mark.unit
    @patch("app.services.schedule_service.datetime")
    def test_skip_past_slot(self, mock_datetime, schedule_service, mock_supabase) -> None:
        """Skips when the slot time is in the past."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            sessions_mock,
            *_rest,
        ) = mock_supabase

        # Fix "now" to Wednesday 2026-02-11 10:00 UTC
        # Slot at 09:00 Taipei = 01:00 UTC -> already past
        fixed_now = datetime(2026, 2, 11, 10, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_datetime.combine = datetime.combine
        mock_datetime.fromisoformat = datetime.fromisoformat

        schedule_row = {
            "id": "sched-past",
            "creator_id": "user-creator",
            "partner_ids": [],
            "days_of_week": [3],  # Wednesday matches
            "slot_time": "09:00:00",  # 09:00 Taipei = 01:00 UTC (past)
            "timezone": "Asia/Taipei",
            "table_mode": "forced_audio",
            "topic": None,
            "max_seats": 4,
            "fill_ai": True,
            "is_active": True,
        }

        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = [
            schedule_row
        ]

        result = schedule_service.create_scheduled_sessions(lookahead_hours=24)

        assert result["sessions_created"] == 0
        sessions_mock.insert.assert_not_called()

    @pytest.mark.unit
    @patch("app.services.schedule_service.datetime")
    def test_skips_banned_partner_invitation(
        self, mock_datetime, schedule_service, mock_supabase
    ) -> None:
        """Skips sending invitation to a currently banned partner."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            sessions_mock,
            session_participants_mock,
            table_invitations_mock,
            users_mock,
        ) = mock_supabase

        fixed_now = datetime(2026, 2, 11, 6, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_datetime.combine = datetime.combine
        mock_datetime.fromisoformat = datetime.fromisoformat

        schedule_row = {
            "id": "sched-wed",
            "creator_id": "user-creator",
            "partner_ids": ["user-banned", "user-ok"],
            "days_of_week": [3],
            "slot_time": "15:00:00",
            "timezone": "Asia/Taipei",
            "table_mode": "forced_audio",
            "topic": None,
            "max_seats": 4,
            "fill_ai": True,
            "is_active": True,
        }

        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = [
            schedule_row
        ]

        # No existing session
        sessions_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        # Session insert succeeds
        sessions_mock.insert.return_value.execute.return_value.data = [{"id": "session-new-2"}]

        # Participant insert succeeds
        session_participants_mock.insert.return_value.execute.return_value.data = [{}]

        # One partner is banned (ban active in the future)
        future_ban = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        users_mock.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "user-banned", "banned_until": future_ban},
            {"id": "user-ok", "banned_until": None},
        ]

        # Invitation insert
        table_invitations_mock.insert.return_value.execute.return_value.data = [{}]

        result = schedule_service.create_scheduled_sessions(lookahead_hours=24)

        assert result["sessions_created"] == 1
        # Only 1 invitation (banned partner skipped)
        assert result["invitations_sent"] == 1

        # Verify invitation was sent only for non-banned partner
        invitation_call = table_invitations_mock.insert.call_args.args[0]
        assert invitation_call["invitee_id"] == "user-ok"

    @pytest.mark.unit
    @patch("app.services.schedule_service.datetime")
    def test_no_active_schedules(self, mock_datetime, schedule_service, mock_supabase) -> None:
        """Returns zeros when no active schedules exist."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            sessions_mock,
            *_rest,
        ) = mock_supabase

        fixed_now = datetime(2026, 2, 11, 6, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now

        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = []

        result = schedule_service.create_scheduled_sessions()

        assert result["sessions_created"] == 0
        assert result["invitations_sent"] == 0

    @pytest.mark.unit
    @patch("app.services.schedule_service.datetime")
    def test_session_end_time_uses_duration_constant(
        self, mock_datetime, schedule_service, mock_supabase
    ) -> None:
        """Verifies the created session end_time is start_time + SESSION_DURATION_MINUTES."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            sessions_mock,
            session_participants_mock,
            _invitations,
            users_mock,
        ) = mock_supabase

        fixed_now = datetime(2026, 2, 11, 6, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_datetime.combine = datetime.combine
        mock_datetime.fromisoformat = datetime.fromisoformat

        schedule_row = {
            "id": "sched-wed",
            "creator_id": "user-creator",
            "partner_ids": [],
            "days_of_week": [3],
            "slot_time": "15:00:00",  # 15:00 Taipei = 07:00 UTC
            "timezone": "Asia/Taipei",
            "table_mode": "forced_audio",
            "topic": None,
            "max_seats": 4,
            "fill_ai": True,
            "is_active": True,
        }

        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = [
            schedule_row
        ]

        sessions_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        sessions_mock.insert.return_value.execute.return_value.data = [{"id": "session-new-3"}]
        session_participants_mock.insert.return_value.execute.return_value.data = [{}]

        schedule_service.create_scheduled_sessions(lookahead_hours=24)

        session_insert_call = sessions_mock.insert.call_args.args[0]
        start_time = datetime.fromisoformat(session_insert_call["start_time"])
        end_time = datetime.fromisoformat(session_insert_call["end_time"])
        assert (end_time - start_time) == timedelta(minutes=SESSION_DURATION_MINUTES)


# =============================================================================
# Internal helpers
# =============================================================================


class TestScheduleToInfo:
    """Tests for _schedule_to_info() helper."""

    @pytest.mark.unit
    def test_normalizes_slot_time_format(
        self, schedule_service, mock_supabase, sample_schedule_row
    ) -> None:
        """Normalizes HH:MM:SS to HH:MM format."""
        _mock, *_, users_mock = mock_supabase

        users_mock.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "user-partner-1", "display_name": "Alice", "username": "alice"}
        ]

        result = schedule_service._schedule_to_info(sample_schedule_row)

        assert result["slot_time"] == "09:00"  # HH:MM:SS -> HH:MM

    @pytest.mark.unit
    def test_handles_missing_optional_fields(self, schedule_service, mock_supabase) -> None:
        """Handles gracefully when optional fields are missing from DB row."""
        _mock, *_, users_mock = mock_supabase

        users_mock.select.return_value.in_.return_value.execute.return_value.data = []

        minimal_row = {
            "id": "sched-minimal",
            "creator_id": "user-123",
        }

        result = schedule_service._schedule_to_info(minimal_row)

        assert result["id"] == "sched-minimal"
        assert result["partner_ids"] == []
        assert result["partner_names"] == []
        assert result["days_of_week"] == []
        assert result["timezone"] == "Asia/Taipei"
        assert result["table_mode"] == "forced_audio"
        assert result["max_seats"] == 4
        assert result["fill_ai"] is True
        assert result["is_active"] is True

    @pytest.mark.unit
    def test_resolves_partner_names_with_fallback(self, schedule_service, mock_supabase) -> None:
        """Falls back to username then 'Unknown' when display_name is missing."""
        _mock, *_, users_mock = mock_supabase

        users_mock.select.return_value.in_.return_value.execute.return_value.data = [
            {"id": "p1", "display_name": "Alice", "username": "alice"},
            {"id": "p2", "display_name": None, "username": "bob_user"},
            # p3 not returned at all (unknown user)
        ]

        row = {
            "id": "sched-test",
            "creator_id": "user-123",
            "partner_ids": ["p1", "p2", "p3"],
        }

        result = schedule_service._schedule_to_info(row)

        assert result["partner_names"] == ["Alice", "bob_user", "Unknown"]

    @pytest.mark.unit
    def test_handles_hhmm_format_slot_time(self, schedule_service, mock_supabase) -> None:
        """Handles slot_time in HH:MM format (without seconds)."""
        _mock, *_, users_mock = mock_supabase

        users_mock.select.return_value.in_.return_value.execute.return_value.data = []

        row = {
            "id": "sched-hhmm",
            "creator_id": "user-123",
            "slot_time": "14:30",  # HH:MM format (no seconds)
        }

        result = schedule_service._schedule_to_info(row)

        assert result["slot_time"] == "14:30"  # Should pass through unchanged


# =============================================================================
# Tomorrow matching
# =============================================================================


class TestTomorrowMatching:
    """Tests for tomorrow's day matching in create_scheduled_sessions."""

    @pytest.mark.unit
    @patch("app.services.schedule_service.datetime")
    def test_creates_session_for_tomorrow(
        self, mock_datetime, schedule_service, mock_supabase
    ) -> None:
        """Creates session when tomorrow's weekday matches the schedule."""
        (
            _mock,
            _credits,
            _partnerships,
            recurring_schedules_mock,
            sessions_mock,
            session_participants_mock,
            _table_invitations,
            _users_mock,
        ) = mock_supabase

        # Fix "now" to Tuesday 2026-02-10 06:00 UTC
        # Tomorrow (Wednesday) isoweekday=3, %7=3 -> day_of_week=3
        fixed_now = datetime(2026, 2, 10, 6, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = fixed_now
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_datetime.combine = datetime.combine
        mock_datetime.fromisoformat = datetime.fromisoformat

        schedule_row = {
            "id": "sched-wed-tomorrow",
            "creator_id": "user-creator",
            "partner_ids": [],  # No partners to simplify test
            "days_of_week": [3],  # Wednesday (tomorrow)
            "slot_time": "09:00:00",  # 09:00 Taipei = 01:00 UTC
            "timezone": "Asia/Taipei",
            "table_mode": "forced_audio",
            "topic": "Tomorrow focus",
            "max_seats": 4,
            "fill_ai": True,
            "is_active": True,
        }

        recurring_schedules_mock.select.return_value.eq.return_value.execute.return_value.data = [
            schedule_row
        ]

        # No existing session
        sessions_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        # Session insert succeeds
        sessions_mock.insert.return_value.execute.return_value.data = [{"id": "session-tomorrow"}]

        # Participant insert succeeds
        session_participants_mock.insert.return_value.execute.return_value.data = [{}]

        result = schedule_service.create_scheduled_sessions(lookahead_hours=48)

        assert result["sessions_created"] == 1
        sessions_mock.insert.assert_called_once()
