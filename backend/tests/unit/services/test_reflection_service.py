"""Unit tests for ReflectionService."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.models.reflection import (
    NotSessionParticipantError,
    ReflectionPhase,
    SessionNotFoundError,
)
from app.services.reflection_service import ReflectionService


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def service(mock_supabase):
    """ReflectionService with mocked Supabase."""
    return ReflectionService(supabase=mock_supabase)


# =============================================================================
# Helpers
# =============================================================================


def _make_reflection_row(
    phase: str = "setup",
    user_id: str = "user-1",
    session_id: str = "session-1",
    content: str = "Working on thesis",
) -> dict:
    """Create a reflection record dict as returned from DB."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": "reflection-id-1",
        "session_id": session_id,
        "user_id": user_id,
        "phase": phase,
        "content": content,
        "created_at": now,
        "updated_at": now,
    }


def _setup_table_router(mock_supabase, table_mocks: dict) -> None:
    """Configure table-specific mock routing."""
    mock_supabase.table.side_effect = lambda name: table_mocks.get(name, MagicMock())


# =============================================================================
# TestSaveReflection
# =============================================================================


class TestSaveReflection:
    """Tests for save_reflection()."""

    @pytest.mark.unit
    def test_save_new_reflection(self, service, mock_supabase) -> None:
        """Successfully save a new reflection."""
        sessions_mock = MagicMock()
        participants_mock = MagicMock()
        reflections_mock = MagicMock()
        users_mock = MagicMock()

        _setup_table_router(
            mock_supabase,
            {
                "sessions": sessions_mock,
                "session_participants": participants_mock,
                "session_reflections": reflections_mock,
                "users": users_mock,
            },
        )

        # Session exists
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]
        # User is participant
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "p-1"}
        ]
        # Upsert returns the row
        row = _make_reflection_row()
        reflections_mock.upsert.return_value.execute.return_value.data = [row]
        # Display name
        users_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"display_name": "Test User", "username": "testuser"}
        ]

        result = service.save_reflection(
            session_id="session-1",
            user_id="user-1",
            phase=ReflectionPhase.SETUP,
            content="Working on thesis",
        )

        assert result.id == "reflection-id-1"
        assert result.phase == ReflectionPhase.SETUP
        assert result.content == "Working on thesis"
        assert result.display_name == "Test User"

        # Verify upsert was called with correct on_conflict
        reflections_mock.upsert.assert_called_once()
        call_kwargs = reflections_mock.upsert.call_args
        assert call_kwargs.kwargs["on_conflict"] == "session_id,user_id,phase"

    @pytest.mark.unit
    def test_save_reflection_session_not_found(self, service, mock_supabase) -> None:
        """Raises SessionNotFoundError when session doesn't exist."""
        sessions_mock = MagicMock()
        _setup_table_router(mock_supabase, {"sessions": sessions_mock})

        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(SessionNotFoundError):
            service.save_reflection(
                session_id="nonexistent",
                user_id="user-1",
                phase=ReflectionPhase.SETUP,
                content="Test",
            )

    @pytest.mark.unit
    def test_save_reflection_not_participant(self, service, mock_supabase) -> None:
        """Raises NotSessionParticipantError when user isn't in session."""
        sessions_mock = MagicMock()
        participants_mock = MagicMock()

        _setup_table_router(
            mock_supabase,
            {
                "sessions": sessions_mock,
                "session_participants": participants_mock,
            },
        )

        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(NotSessionParticipantError):
            service.save_reflection(
                session_id="session-1",
                user_id="outsider",
                phase=ReflectionPhase.SETUP,
                content="Test",
            )

    @pytest.mark.unit
    def test_save_reflection_truncates_long_content(self, service, mock_supabase) -> None:
        """Content is truncated to 500 characters."""
        sessions_mock = MagicMock()
        participants_mock = MagicMock()
        reflections_mock = MagicMock()
        users_mock = MagicMock()

        _setup_table_router(
            mock_supabase,
            {
                "sessions": sessions_mock,
                "session_participants": participants_mock,
                "session_reflections": reflections_mock,
                "users": users_mock,
            },
        )

        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "p-1"}
        ]
        row = _make_reflection_row(content="x" * 500)
        reflections_mock.upsert.return_value.execute.return_value.data = [row]
        users_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"display_name": None, "username": "testuser"}
        ]

        long_content = "x" * 600
        service.save_reflection(
            session_id="session-1",
            user_id="user-1",
            phase=ReflectionPhase.SETUP,
            content=long_content,
        )

        # Verify the upserted content was truncated
        upsert_args = reflections_mock.upsert.call_args.args[0]
        assert len(upsert_args["content"]) == 500

    @pytest.mark.unit
    def test_save_reflection_skips_db_when_display_name_provided(
        self, service, mock_supabase
    ) -> None:
        """Skips _get_display_name DB query when display_name is provided."""
        sessions_mock = MagicMock()
        participants_mock = MagicMock()
        reflections_mock = MagicMock()
        users_mock = MagicMock()

        _setup_table_router(
            mock_supabase,
            {
                "sessions": sessions_mock,
                "session_participants": participants_mock,
                "session_reflections": reflections_mock,
                "users": users_mock,
            },
        )

        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "p-1"}
        ]
        reflections_mock.upsert.return_value.execute.return_value.data = [_make_reflection_row()]

        result = service.save_reflection(
            session_id="session-1",
            user_id="user-1",
            phase=ReflectionPhase.SETUP,
            content="Working on thesis",
            display_name="Provided Name",
        )

        assert result.display_name == "Provided Name"
        # Users table should NOT be queried when display_name is provided
        users_mock.select.assert_not_called()

    @pytest.mark.unit
    def test_save_reflection_falls_back_to_username(self, service, mock_supabase) -> None:
        """Uses username when display_name is None."""
        sessions_mock = MagicMock()
        participants_mock = MagicMock()
        reflections_mock = MagicMock()
        users_mock = MagicMock()

        _setup_table_router(
            mock_supabase,
            {
                "sessions": sessions_mock,
                "session_participants": participants_mock,
                "session_reflections": reflections_mock,
                "users": users_mock,
            },
        )

        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "p-1"}
        ]
        reflections_mock.upsert.return_value.execute.return_value.data = [_make_reflection_row()]
        users_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"display_name": None, "username": "fallback_name"}
        ]

        result = service.save_reflection(
            session_id="session-1",
            user_id="user-1",
            phase=ReflectionPhase.SETUP,
            content="Test",
        )

        assert result.display_name == "fallback_name"


# =============================================================================
# TestGetSessionReflections
# =============================================================================


class TestGetSessionReflections:
    """Tests for get_session_reflections()."""

    @pytest.mark.unit
    def test_returns_all_reflections(self, service, mock_supabase) -> None:
        """Returns reflections from all users in chronological order."""
        sessions_mock = MagicMock()
        reflections_mock = MagicMock()

        _setup_table_router(
            mock_supabase,
            {
                "sessions": sessions_mock,
                "session_reflections": reflections_mock,
            },
        )

        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]

        now = datetime.now(timezone.utc).isoformat()
        reflections_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            {
                "id": "r-1",
                "session_id": "session-1",
                "user_id": "user-1",
                "phase": "setup",
                "content": "Goal 1",
                "created_at": now,
                "updated_at": now,
                "users": {"display_name": "Alice", "username": "alice"},
            },
            {
                "id": "r-2",
                "session_id": "session-1",
                "user_id": "user-2",
                "phase": "setup",
                "content": "Goal 2",
                "created_at": now,
                "updated_at": now,
                "users": {"display_name": None, "username": "bob"},
            },
        ]

        result = service.get_session_reflections("session-1")

        assert len(result) == 2
        assert result[0].display_name == "Alice"
        assert result[1].display_name == "bob"  # Falls back to username
        assert result[0].content == "Goal 1"

    @pytest.mark.unit
    def test_empty_session_returns_empty_list(self, service, mock_supabase) -> None:
        """Returns empty list when no reflections exist."""
        sessions_mock = MagicMock()
        reflections_mock = MagicMock()

        _setup_table_router(
            mock_supabase,
            {
                "sessions": sessions_mock,
                "session_reflections": reflections_mock,
            },
        )

        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]
        reflections_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

        result = service.get_session_reflections("session-1")
        assert result == []

    @pytest.mark.unit
    def test_session_not_found_raises(self, service, mock_supabase) -> None:
        """Raises SessionNotFoundError for nonexistent session."""
        sessions_mock = MagicMock()
        _setup_table_router(mock_supabase, {"sessions": sessions_mock})
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(SessionNotFoundError):
            service.get_session_reflections("nonexistent")


# =============================================================================
# TestGetDiary
# =============================================================================


class TestGetDiary:
    """Tests for get_diary()."""

    def _setup_diary_mocks(
        self, mock_supabase, reflections_data, notes_data=None, participants_data=None
    ):
        """Helper to set up all diary-related table mocks."""
        reflections_mock = MagicMock()
        notes_mock = MagicMock()
        participants_mock = MagicMock()

        _setup_table_router(
            mock_supabase,
            {
                "session_reflections": reflections_mock,
                "diary_notes": notes_mock,
                "session_participants": participants_mock,
            },
        )

        # Reflections query (with join + order)
        reflections_mock.select.return_value.eq.return_value.order.return_value.execute.return_value.data = reflections_data
        # Diary notes query
        notes_mock.select.return_value.eq.return_value.execute.return_value.data = notes_data or []
        # Participants query (focus minutes)
        participants_mock.select.return_value.eq.return_value.execute.return_value.data = (
            participants_data or []
        )

        return reflections_mock, notes_mock, participants_mock

    @pytest.mark.unit
    def test_groups_by_session(self, service, mock_supabase) -> None:
        """Reflections are grouped by session in the diary."""
        now = datetime.now(timezone.utc).isoformat()
        earlier = "2026-02-07T10:00:00+00:00"

        self._setup_diary_mocks(
            mock_supabase,
            reflections_data=[
                {
                    "session_id": "session-1",
                    "phase": "setup",
                    "content": "Goal A",
                    "created_at": now,
                    "sessions": {"start_time": now, "topic": "Deep Work"},
                },
                {
                    "session_id": "session-1",
                    "phase": "break",
                    "content": "Going well",
                    "created_at": now,
                    "sessions": {"start_time": now, "topic": "Deep Work"},
                },
                {
                    "session_id": "session-2",
                    "phase": "setup",
                    "content": "Goal B",
                    "created_at": earlier,
                    "sessions": {"start_time": earlier, "topic": None},
                },
            ],
            participants_data=[
                {"session_id": "session-1", "total_active_minutes": 45},
                {"session_id": "session-2", "total_active_minutes": 30},
            ],
        )

        result = service.get_diary(user_id="user-1", page=1, per_page=20)

        assert result.total == 2
        assert len(result.items) == 2
        assert result.items[0].session_id == "session-1"
        assert len(result.items[0].reflections) == 2
        assert result.items[0].focus_minutes == 45
        assert result.items[1].session_id == "session-2"
        assert len(result.items[1].reflections) == 1

    @pytest.mark.unit
    def test_diary_pagination(self, service, mock_supabase) -> None:
        """Diary respects page and per_page parameters."""
        now = datetime.now(timezone.utc).isoformat()

        self._setup_diary_mocks(
            mock_supabase,
            reflections_data=[
                {
                    "session_id": f"session-{i}",
                    "phase": "setup",
                    "content": f"Goal {i}",
                    "created_at": now,
                    "sessions": {"start_time": now, "topic": None},
                }
                for i in range(3)
            ],
        )

        result = service.get_diary(user_id="user-1", page=1, per_page=2)

        assert result.total == 3
        assert len(result.items) == 2
        assert result.page == 1
        assert result.per_page == 2

    @pytest.mark.unit
    def test_diary_empty(self, service, mock_supabase) -> None:
        """Returns empty diary when user has no reflections."""
        self._setup_diary_mocks(mock_supabase, reflections_data=[])

        result = service.get_diary(user_id="user-1")

        assert result.total == 0
        assert result.items == []

    @pytest.mark.unit
    def test_diary_sorts_reflections_by_phase_order(self, service, mock_supabase) -> None:
        """Within a session, reflections are ordered: setup, break, social."""
        now = datetime.now(timezone.utc).isoformat()

        self._setup_diary_mocks(
            mock_supabase,
            reflections_data=[
                {
                    "session_id": "session-1",
                    "phase": "social",
                    "content": "Afterthoughts",
                    "created_at": now,
                    "sessions": {"start_time": now, "topic": None},
                },
                {
                    "session_id": "session-1",
                    "phase": "setup",
                    "content": "My goal",
                    "created_at": now,
                    "sessions": {"start_time": now, "topic": None},
                },
                {
                    "session_id": "session-1",
                    "phase": "break",
                    "content": "Check-in",
                    "created_at": now,
                    "sessions": {"start_time": now, "topic": None},
                },
            ],
        )

        result = service.get_diary(user_id="user-1")

        phases = [r.phase for r in result.items[0].reflections]
        assert phases == [ReflectionPhase.SETUP, ReflectionPhase.BREAK, ReflectionPhase.SOCIAL]

    @pytest.mark.unit
    def test_diary_includes_notes_and_tags(self, service, mock_supabase) -> None:
        """Diary entries include post-session notes and tags."""
        now = datetime.now(timezone.utc).isoformat()

        self._setup_diary_mocks(
            mock_supabase,
            reflections_data=[
                {
                    "session_id": "session-1",
                    "phase": "setup",
                    "content": "Goal",
                    "created_at": now,
                    "sessions": {"start_time": now, "topic": "Coding"},
                },
            ],
            notes_data=[
                {
                    "session_id": "session-1",
                    "note": "Great session!",
                    "tags": ["productive", "breakthrough"],
                },
            ],
        )

        result = service.get_diary(user_id="user-1")

        assert result.items[0].note == "Great session!"
        assert result.items[0].tags == ["productive", "breakthrough"]

    @pytest.mark.unit
    def test_diary_search_filters_by_content(self, service, mock_supabase) -> None:
        """Search filters diary entries by reflection content."""
        now = datetime.now(timezone.utc).isoformat()
        earlier = "2026-02-07T10:00:00+00:00"

        self._setup_diary_mocks(
            mock_supabase,
            reflections_data=[
                {
                    "session_id": "session-1",
                    "phase": "setup",
                    "content": "Working on Python project",
                    "created_at": now,
                    "sessions": {"start_time": now, "topic": None},
                },
                {
                    "session_id": "session-2",
                    "phase": "setup",
                    "content": "Reading documentation",
                    "created_at": earlier,
                    "sessions": {"start_time": earlier, "topic": None},
                },
            ],
        )

        result = service.get_diary(user_id="user-1", search="Python")

        assert len(result.items) == 1
        assert result.items[0].session_id == "session-1"

    @pytest.mark.unit
    def test_diary_search_filters_by_note(self, service, mock_supabase) -> None:
        """Search also matches against diary notes."""
        now = datetime.now(timezone.utc).isoformat()

        self._setup_diary_mocks(
            mock_supabase,
            reflections_data=[
                {
                    "session_id": "session-1",
                    "phase": "setup",
                    "content": "Goal A",
                    "created_at": now,
                    "sessions": {"start_time": now, "topic": None},
                },
            ],
            notes_data=[
                {
                    "session_id": "session-1",
                    "note": "Breakthrough on thesis chapter 3",
                    "tags": ["breakthrough"],
                },
            ],
        )

        result = service.get_diary(user_id="user-1", search="thesis")

        assert len(result.items) == 1


# =============================================================================
# TestSaveDiaryNote
# =============================================================================


class TestSaveDiaryNote:
    """Tests for save_diary_note()."""

    @pytest.mark.unit
    def test_save_note_success(self, service, mock_supabase) -> None:
        """Successfully saves a diary note with tags."""
        sessions_mock = MagicMock()
        participants_mock = MagicMock()
        notes_mock = MagicMock()

        _setup_table_router(
            mock_supabase,
            {
                "sessions": sessions_mock,
                "session_participants": participants_mock,
                "diary_notes": notes_mock,
            },
        )

        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "p-1"}
        ]

        now = datetime.now(timezone.utc).isoformat()
        notes_mock.upsert.return_value.execute.return_value.data = [
            {
                "session_id": "session-1",
                "user_id": "user-1",
                "note": "Productive day!",
                "tags": ["productive", "energized"],
                "created_at": now,
                "updated_at": now,
            }
        ]

        result = service.save_diary_note(
            session_id="session-1",
            user_id="user-1",
            note="Productive day!",
            tags=["productive", "energized"],
        )

        assert result.session_id == "session-1"
        assert result.note == "Productive day!"
        assert result.tags == ["productive", "energized"]
        notes_mock.upsert.assert_called_once()

    @pytest.mark.unit
    def test_save_note_invalid_tags(self, service, mock_supabase) -> None:
        """Raises ValueError for invalid tags."""
        sessions_mock = MagicMock()
        participants_mock = MagicMock()

        _setup_table_router(
            mock_supabase,
            {
                "sessions": sessions_mock,
                "session_participants": participants_mock,
            },
        )

        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "p-1"}
        ]

        with pytest.raises(ValueError, match="Invalid tags"):
            service.save_diary_note(
                session_id="session-1",
                user_id="user-1",
                note="Test",
                tags=["invalid-tag"],
            )

    @pytest.mark.unit
    def test_save_note_session_not_found(self, service, mock_supabase) -> None:
        """Raises SessionNotFoundError for nonexistent session."""
        sessions_mock = MagicMock()
        _setup_table_router(mock_supabase, {"sessions": sessions_mock})
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(SessionNotFoundError):
            service.save_diary_note(
                session_id="nonexistent",
                user_id="user-1",
                note="Test",
                tags=[],
            )

    @pytest.mark.unit
    def test_save_note_not_participant(self, service, mock_supabase) -> None:
        """Raises NotSessionParticipantError for non-participants."""
        sessions_mock = MagicMock()
        participants_mock = MagicMock()

        _setup_table_router(
            mock_supabase,
            {
                "sessions": sessions_mock,
                "session_participants": participants_mock,
            },
        )

        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        with pytest.raises(NotSessionParticipantError):
            service.save_diary_note(
                session_id="session-1",
                user_id="outsider",
                note="Test",
                tags=[],
            )


# =============================================================================
# TestGetDiaryStats
# =============================================================================


class TestGetDiaryStats:
    """Tests for get_diary_stats()."""

    @pytest.mark.unit
    def test_returns_stats(self, service, mock_supabase) -> None:
        """Returns user diary statistics."""
        users_mock = MagicMock()
        participants_mock = MagicMock()

        _setup_table_router(
            mock_supabase,
            {
                "users": users_mock,
                "session_participants": participants_mock,
            },
        )

        users_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"current_streak": 5, "total_focus_minutes": 500, "session_count": 12}
        ]
        participants_mock.select.return_value.eq.return_value.gte.return_value.execute.return_value.data = [
            {"total_active_minutes": 45},
            {"total_active_minutes": 50},
        ]

        result = service.get_diary_stats(user_id="user-1")

        assert result.current_streak == 5
        assert result.weekly_focus_minutes == 95
        assert result.total_sessions == 12

    @pytest.mark.unit
    def test_returns_zero_stats_for_unknown_user(self, service, mock_supabase) -> None:
        """Returns zero stats when user not found."""
        users_mock = MagicMock()
        _setup_table_router(mock_supabase, {"users": users_mock})

        users_mock.select.return_value.eq.return_value.execute.return_value.data = []

        result = service.get_diary_stats(user_id="nonexistent")

        assert result.current_streak == 0
        assert result.weekly_focus_minutes == 0
        assert result.total_sessions == 0
