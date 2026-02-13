"""Unit tests for webhook handlers (WU3).

Tests:
- livekit_webhook() signature validation based on environment
- is_session_completed() with various scenarios
- _parse_session_start_time() helper
- _handle_participant_left event processing
- _handle_room_finished event processing
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.routers.webhooks import (
    _create_pending_ratings,
    _event_to_dict,
    _handle_participant_joined,
    _handle_participant_left,
    _handle_room_finished,
    _handle_track_published,
    _parse_session_start_time,
    is_session_completed,
    livekit_webhook,
)

# =============================================================================
# Webhook Signature Validation Tests
# =============================================================================


class TestWebhookSignatureValidation:
    """Test webhook signature validation based on environment."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_webhook_skips_signature_in_development_with_placeholder_key(self) -> None:
        """Signature validation skipped only when BOTH dev mode AND placeholder key."""
        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=b'{"event": "test"}')

        mock_settings = MagicMock()
        mock_settings.environment = "development"
        mock_settings.livekit_api_key = "your-livekit-api-key"  # Placeholder
        mock_settings.livekit_api_secret = "your-livekit-api-secret"

        with patch("app.routers.webhooks.get_settings", return_value=mock_settings):
            with patch("app.routers.webhooks.logger") as mock_logger:
                result = await livekit_webhook(mock_request, authorization=None)
                assert result == {"status": "ok"}
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_webhook_validates_in_development_with_real_key(self) -> None:
        """Defense-in-depth: validates signature in dev mode if real API key is set."""
        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=b'{"event": "test"}')

        mock_settings = MagicMock()
        mock_settings.environment = "development"
        mock_settings.livekit_api_key = "real-key"  # Real key, not placeholder
        mock_settings.livekit_api_secret = "real-secret"

        with patch("app.routers.webhooks.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await livekit_webhook(mock_request, authorization="invalid-sig")
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_webhook_validates_signature_in_production(self) -> None:
        """Signature validation required in production environment."""
        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=b'{"event": "test"}')

        mock_settings = MagicMock()
        mock_settings.environment = "production"
        mock_settings.livekit_api_key = "real-key"
        mock_settings.livekit_api_secret = "real-secret"

        with patch("app.routers.webhooks.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await livekit_webhook(mock_request, authorization="invalid-sig")
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_webhook_validates_signature_in_staging(self) -> None:
        """Signature validation required in staging environment."""
        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=b'{"event": "test"}')

        mock_settings = MagicMock()
        mock_settings.environment = "staging"
        mock_settings.livekit_api_key = "real-key"
        mock_settings.livekit_api_secret = "real-secret"

        with patch("app.routers.webhooks.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await livekit_webhook(mock_request, authorization="invalid-sig")
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_webhook_rejects_invalid_json_in_development(self) -> None:
        """Returns 400 for invalid JSON even in development with placeholder key."""
        mock_request = MagicMock()
        mock_request.body = AsyncMock(return_value=b"not valid json")

        mock_settings = MagicMock()
        mock_settings.environment = "development"
        mock_settings.livekit_api_key = "your-livekit-api-key"  # Placeholder

        with patch("app.routers.webhooks.get_settings", return_value=mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                await livekit_webhook(mock_request, authorization=None)
            assert exc_info.value.status_code == 400
            assert "Invalid JSON" in exc_info.value.detail


# =============================================================================
# is_session_completed() Tests
# =============================================================================


class TestIsSessionCompleted:
    """Tests for the is_session_completed() helper."""

    @pytest.fixture
    def session_start(self):
        """Session that started 55 minutes ago."""
        return datetime.now(timezone.utc) - timedelta(minutes=55)

    @pytest.mark.unit
    def test_completed_still_present_with_sufficient_time(self, session_start) -> None:
        """User still present (left_at=None) with 30 active minutes = completed."""
        participant = {"left_at": None, "total_active_minutes": 30}
        assert is_session_completed(participant, session_start) is True

    @pytest.mark.unit
    def test_not_completed_insufficient_active_minutes(self, session_start) -> None:
        """User present but only 10 active minutes = not completed."""
        participant = {"left_at": None, "total_active_minutes": 10}
        assert is_session_completed(participant, session_start) is False

    @pytest.mark.unit
    def test_not_completed_zero_active_minutes(self, session_start) -> None:
        """User with 0 active minutes = not completed."""
        participant = {"left_at": None, "total_active_minutes": 0}
        assert is_session_completed(participant, session_start) is False

    @pytest.mark.unit
    def test_not_completed_null_active_minutes(self, session_start) -> None:
        """User with null active minutes = not completed."""
        participant = {"left_at": None, "total_active_minutes": None}
        assert is_session_completed(participant, session_start) is False

    @pytest.mark.unit
    def test_completed_left_after_minute_50(self, session_start) -> None:
        """User left at minute 52 with 25 active minutes = completed."""
        left_at = (session_start + timedelta(minutes=52)).isoformat()
        participant = {"left_at": left_at, "total_active_minutes": 25}
        assert is_session_completed(participant, session_start) is True

    @pytest.mark.unit
    def test_not_completed_left_before_minute_50(self, session_start) -> None:
        """User left at minute 40 with 30 active minutes = not completed."""
        left_at = (session_start + timedelta(minutes=40)).isoformat()
        participant = {"left_at": left_at, "total_active_minutes": 30}
        assert is_session_completed(participant, session_start) is False

    @pytest.mark.unit
    def test_completed_left_exactly_at_minute_50(self, session_start) -> None:
        """User left exactly at minute 50 = completed (boundary case)."""
        left_at = (session_start + timedelta(minutes=50)).isoformat()
        participant = {"left_at": left_at, "total_active_minutes": 25}
        assert is_session_completed(participant, session_start) is True

    @pytest.mark.unit
    def test_not_completed_left_at_minute_49(self, session_start) -> None:
        """User left at minute 49 = not completed (just before boundary)."""
        left_at = (session_start + timedelta(minutes=49)).isoformat()
        participant = {"left_at": left_at, "total_active_minutes": 25}
        assert is_session_completed(participant, session_start) is False

    @pytest.mark.unit
    def test_handles_z_suffix_in_left_at(self, session_start) -> None:
        """Handles ISO timestamps ending with Z."""
        left_at_dt = session_start + timedelta(minutes=52)
        left_at = left_at_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        participant = {"left_at": left_at, "total_active_minutes": 25}
        assert is_session_completed(participant, session_start) is True

    @pytest.mark.unit
    def test_minimum_active_minutes_boundary(self, session_start) -> None:
        """Exactly 20 active minutes = completed (boundary)."""
        participant = {"left_at": None, "total_active_minutes": 20}
        assert is_session_completed(participant, session_start) is True

    @pytest.mark.unit
    def test_below_minimum_active_minutes(self, session_start) -> None:
        """19 active minutes = not completed (just below boundary)."""
        participant = {"left_at": None, "total_active_minutes": 19}
        assert is_session_completed(participant, session_start) is False


# =============================================================================
# _parse_session_start_time() Tests
# =============================================================================


class TestParseSessionStartTime:
    """Tests for the _parse_session_start_time() helper."""

    @pytest.mark.unit
    def test_parses_iso_format(self) -> None:
        """Parses standard ISO format with timezone."""
        result = _parse_session_start_time("2025-02-07T10:00:00+00:00")
        assert result.hour == 10
        assert result.tzinfo is not None

    @pytest.mark.unit
    def test_parses_z_suffix(self) -> None:
        """Parses ISO format with Z suffix."""
        result = _parse_session_start_time("2025-02-07T10:00:00.000Z")
        assert result.hour == 10

    @pytest.mark.unit
    def test_returns_datetime_unchanged(self) -> None:
        """Returns datetime objects unchanged."""
        dt = datetime(2025, 2, 7, 10, 0, tzinfo=timezone.utc)
        result = _parse_session_start_time(dt)
        assert result is dt


# =============================================================================
# _handle_participant_left Tests
# =============================================================================


class TestHandleParticipantLeft:
    """Tests for the _handle_participant_left() handler."""

    @pytest.fixture
    def mock_supabase(self):
        mock = MagicMock()
        return mock

    @pytest.fixture
    def left_event(self):
        """Standard participant_left event data."""
        return {
            "event": "participant_left",
            "room": {"name": "focus-abc123"},
            "participant": {"identity": "user-123", "sid": "PA_123"},
        }

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_calculates_active_minutes_from_connection(self, left_event) -> None:
        """Calculates active minutes from connected_at to now."""
        mock_supabase = MagicMock()

        # Connected 30 minutes ago
        connected_at = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()

        # Cache table mocks by name
        sessions_mock = MagicMock()
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]

        participants_mock = MagicMock()
        # select(...).eq(...).eq(...).execute() for participant lookup
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {
                "id": "p-1",
                "connected_at": connected_at,
                "total_active_minutes": 0,
                "disconnect_count": 0,
            }
        ]
        # update(...).eq(...).execute() for updating
        participants_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        table_cache = {"sessions": sessions_mock, "session_participants": participants_mock}
        mock_supabase.table.side_effect = lambda name: table_cache[name]

        with patch("app.routers.webhooks.get_supabase", return_value=mock_supabase):
            await _handle_participant_left(left_event)

        # Verify update was called on the participants table
        assert participants_mock.update.called
        update_data = participants_mock.update.call_args.args[0]
        assert update_data["is_connected"] is False
        assert update_data["total_active_minutes"] >= 29  # ~30 min connected

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_skips_if_no_room_name(self) -> None:
        """Returns silently if room name is missing."""
        event = {"event": "participant_left", "room": {}, "participant": {"identity": "u-1"}}
        # Should not raise
        with patch("app.routers.webhooks.get_supabase") as mock_get:
            await _handle_participant_left(event)
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_skips_if_no_identity(self) -> None:
        """Returns silently if participant identity is missing."""
        event = {"event": "participant_left", "room": {"name": "room-1"}, "participant": {}}
        with patch("app.routers.webhooks.get_supabase") as mock_get:
            await _handle_participant_left(event)
            mock_get.assert_not_called()


# =============================================================================
# _handle_room_finished Tests
# =============================================================================


class TestHandleRoomFinished:
    """Tests for the _handle_room_finished() handler."""

    @pytest.fixture
    def room_finished_event(self):
        return {
            "event": "room_finished",
            "room": {"name": "focus-abc123", "sid": "RM_123"},
        }

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_marks_session_ended(self, room_finished_event) -> None:
        """Sets current_phase to 'ended' when room finishes."""
        mock_supabase = MagicMock()

        session_start = (datetime.now(timezone.utc) - timedelta(minutes=55)).isoformat()

        # Cache table mocks
        sessions_mock = MagicMock()
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1", "start_time": session_start, "current_phase": "social"}
        ]
        sessions_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        participants_mock = MagicMock()
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        table_cache = {"sessions": sessions_mock, "session_participants": participants_mock}
        mock_supabase.table.side_effect = lambda name: table_cache.get(name, MagicMock())

        with patch("app.routers.webhooks.get_supabase", return_value=mock_supabase):
            await _handle_room_finished(room_finished_event)

        # Verify session was marked as ended
        sessions_mock.update.assert_called()
        update_data = sessions_mock.update.call_args.args[0]
        assert update_data["current_phase"] == "ended"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_awards_essence_to_qualifying_participants(self, room_finished_event) -> None:
        """Awards essence to participants who completed the session."""
        mock_supabase = MagicMock()

        session_start = (datetime.now(timezone.utc) - timedelta(minutes=55)).isoformat()

        # Cache table mocks
        sessions_mock = MagicMock()
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1", "start_time": session_start, "current_phase": "social"}
        ]
        sessions_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        participants_mock = MagicMock()
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {
                "id": "p-1",
                "user_id": "user-1",
                "left_at": None,
                "total_active_minutes": 30,
                "essence_earned": False,
            },
            {
                "id": "p-2",
                "user_id": "user-2",
                "left_at": None,
                "total_active_minutes": 10,
                "essence_earned": False,
            },
        ]
        participants_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        essence_mock = MagicMock()
        essence_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"balance": 5, "total_earned": 5}
        ]
        essence_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        transactions_mock = MagicMock()
        transactions_mock.insert.return_value.execute.return_value.data = [{}]

        table_cache = {
            "sessions": sessions_mock,
            "session_participants": participants_mock,
            "furniture_essence": essence_mock,
            "essence_transactions": transactions_mock,
        }
        mock_supabase.table.side_effect = lambda name: table_cache.get(name, MagicMock())

        with patch("app.routers.webhooks.get_supabase", return_value=mock_supabase):
            await _handle_room_finished(room_finished_event)

        # Verify essence_transactions.insert was called (for qualifying user-1)
        assert transactions_mock.insert.called
        # Verify participant essence_earned was marked
        assert participants_mock.update.called

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_skips_if_no_room_name(self) -> None:
        """Returns silently if room name is missing."""
        event = {"event": "room_finished", "room": {}}
        with patch("app.routers.webhooks.get_supabase") as mock_get:
            await _handle_room_finished(event)
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_skips_if_session_not_found(self) -> None:
        """Returns silently if session not found for room."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []
        mock_supabase.table.return_value = mock_table

        event = {"event": "room_finished", "room": {"name": "nonexistent-room"}}

        with patch("app.routers.webhooks.get_supabase", return_value=mock_supabase):
            await _handle_room_finished(event)

        # Should not call update (no session found)
        mock_table.update.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_inserts_new_essence_record(self) -> None:
        """Inserts a new furniture_essence record when none exists for the user."""
        mock_supabase = MagicMock()

        session_start = (datetime.now(timezone.utc) - timedelta(minutes=55)).isoformat()

        sessions_mock = MagicMock()
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1", "start_time": session_start, "current_phase": "social"}
        ]
        sessions_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        participants_mock = MagicMock()
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {
                "id": "p-1",
                "user_id": "user-new",
                "left_at": None,
                "total_active_minutes": 30,
                "essence_earned": False,
            }
        ]
        participants_mock.update.return_value.eq.return_value.execute.return_value.data = [{}]

        essence_mock = MagicMock()
        # No existing essence record
        essence_mock.select.return_value.eq.return_value.execute.return_value.data = []
        essence_mock.insert.return_value.execute.return_value.data = [{}]

        transactions_mock = MagicMock()
        transactions_mock.insert.return_value.execute.return_value.data = [{}]

        table_cache = {
            "sessions": sessions_mock,
            "session_participants": participants_mock,
            "furniture_essence": essence_mock,
            "essence_transactions": transactions_mock,
        }
        mock_supabase.table.side_effect = lambda name: table_cache.get(name, MagicMock())

        event = {"event": "room_finished", "room": {"name": "focus-abc123", "sid": "RM_123"}}

        with patch("app.routers.webhooks.get_supabase", return_value=mock_supabase):
            await _handle_room_finished(event)

        # Verify insert was called on furniture_essence (not update)
        assert essence_mock.insert.called
        insert_data = essence_mock.insert.call_args.args[0]
        assert insert_data["user_id"] == "user-new"
        assert insert_data["balance"] == 1
        assert insert_data["total_earned"] == 1
        # update should NOT have been called on essence
        essence_mock.update.assert_not_called()


# =============================================================================
# _handle_participant_joined Tests
# =============================================================================


class TestHandleParticipantJoined:
    """Tests for the _handle_participant_joined() handler."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_updates_connection_status(self) -> None:
        """Updates session_participants with connected_at and is_connected=True."""
        mock_supabase = MagicMock()

        sessions_mock = MagicMock()
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]

        participants_mock = MagicMock()
        participants_mock.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {}
        ]

        table_cache = {"sessions": sessions_mock, "session_participants": participants_mock}
        mock_supabase.table.side_effect = lambda name: table_cache[name]

        event = {
            "event": "participant_joined",
            "room": {"name": "focus-abc123"},
            "participant": {"identity": "user-123"},
        }

        with patch("app.routers.webhooks.get_supabase", return_value=mock_supabase):
            await _handle_participant_joined(event)

        # Verify update called
        assert participants_mock.update.called
        update_data = participants_mock.update.call_args.args[0]
        assert update_data["is_connected"] is True
        assert "connected_at" in update_data

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_skips_if_no_room_name(self) -> None:
        """Returns silently if room name is missing."""
        event = {
            "event": "participant_joined",
            "room": {},
            "participant": {"identity": "user-123"},
        }
        with patch("app.routers.webhooks.get_supabase") as mock_get:
            await _handle_participant_joined(event)
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_skips_if_session_not_found(self) -> None:
        """Returns silently if session not found for the room."""
        mock_supabase = MagicMock()

        sessions_mock = MagicMock()
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = []

        table_cache = {"sessions": sessions_mock}
        mock_supabase.table.side_effect = lambda name: table_cache[name]

        event = {
            "event": "participant_joined",
            "room": {"name": "focus-unknown"},
            "participant": {"identity": "user-123"},
        }

        with patch("app.routers.webhooks.get_supabase", return_value=mock_supabase):
            await _handle_participant_joined(event)

        # Should not attempt to update participants since session was not found
        assert "session_participants" not in [
            call.args[0] for call in mock_supabase.table.call_args_list
        ]


# =============================================================================
# _handle_track_published Tests
# =============================================================================


class TestHandleTrackPublished:
    """Tests for the _handle_track_published() handler."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_logs_without_error(self) -> None:
        """Calling with valid event data should not raise any exception."""
        event = {
            "event": "track_published",
            "room": {"name": "focus-abc123"},
            "participant": {"identity": "user-123", "sid": "PA_123"},
            "track": {"type": "audio", "source": "microphone", "sid": "TR_1"},
        }
        # Should not raise
        await _handle_track_published(event)


# =============================================================================
# _handle_participant_left Additional Tests
# =============================================================================


class TestHandleParticipantLeftEdgeCases:
    """Additional edge case tests for _handle_participant_left()."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_skips_if_session_not_found(self) -> None:
        """Returns silently if session not found for the room."""
        mock_supabase = MagicMock()

        sessions_mock = MagicMock()
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = []

        table_cache = {"sessions": sessions_mock}
        mock_supabase.table.side_effect = lambda name: table_cache[name]

        event = {
            "event": "participant_left",
            "room": {"name": "focus-unknown"},
            "participant": {"identity": "user-123"},
        }

        with patch("app.routers.webhooks.get_supabase", return_value=mock_supabase):
            await _handle_participant_left(event)

        # Should not attempt to access session_participants
        table_names = [call.args[0] for call in mock_supabase.table.call_args_list]
        assert "session_participants" not in table_names

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_skips_if_participant_not_found(self) -> None:
        """Returns silently if participant record not found in session."""
        mock_supabase = MagicMock()

        sessions_mock = MagicMock()
        sessions_mock.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "session-1"}
        ]

        participants_mock = MagicMock()
        # Participant lookup returns empty
        participants_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        table_cache = {"sessions": sessions_mock, "session_participants": participants_mock}
        mock_supabase.table.side_effect = lambda name: table_cache[name]

        event = {
            "event": "participant_left",
            "room": {"name": "focus-abc123"},
            "participant": {"identity": "user-ghost"},
        }

        with patch("app.routers.webhooks.get_supabase", return_value=mock_supabase):
            await _handle_participant_left(event)

        # Should not call update since participant was not found
        participants_mock.update.assert_not_called()


# =============================================================================
# _event_to_dict Tests
# =============================================================================


class TestEventToDict:
    """Tests for the _event_to_dict() helper."""

    @pytest.mark.unit
    def test_converts_event_to_dict(self) -> None:
        """Converts a WebhookEvent mock to a well-structured dict."""
        mock_event = MagicMock()
        mock_event.event = "participant_joined"
        mock_event.room.name = "focus-abc"
        mock_event.room.sid = "RM_123"
        mock_event.participant.identity = "user-1"
        mock_event.participant.sid = "PA_1"
        mock_event.participant.name = "Test User"
        mock_event.track.type = "audio"
        mock_event.track.source = "microphone"
        mock_event.track.sid = "TR_1"

        result = _event_to_dict(mock_event)

        assert result["event"] == "participant_joined"
        assert result["room"]["name"] == "focus-abc"
        assert result["room"]["sid"] == "RM_123"
        assert result["participant"]["identity"] == "user-1"
        assert result["participant"]["sid"] == "PA_1"
        assert result["participant"]["name"] == "Test User"
        assert result["track"]["type"] == "audio"
        assert result["track"]["source"] == "microphone"
        assert result["track"]["sid"] == "TR_1"


# =============================================================================
# _create_pending_ratings Tests
# =============================================================================


class TestCreatePendingRatings:
    """Tests for the _create_pending_ratings() helper."""

    @pytest.mark.unit
    def test_creates_pending_ratings_for_all_participants(self) -> None:
        """Creates pending_ratings for each human participant."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value.data = [{}]
        mock_supabase.table.return_value = mock_table

        participants = [
            {"user_id": "user-1", "participant_type": "human"},
            {"user_id": "user-2", "participant_type": "human"},
            {"user_id": "user-3", "participant_type": "human"},
        ]

        count = _create_pending_ratings(mock_supabase, "session-1", participants)

        assert count == 3
        assert mock_table.insert.call_count == 3

    @pytest.mark.unit
    def test_pending_ratings_excludes_self(self) -> None:
        """Each pending_rating's rateable_user_ids excludes the user themselves."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value.data = [{}]
        mock_supabase.table.return_value = mock_table

        participants = [
            {"user_id": "user-1", "participant_type": "human"},
            {"user_id": "user-2", "participant_type": "human"},
        ]

        _create_pending_ratings(mock_supabase, "session-1", participants)

        # Check insert calls
        calls = mock_table.insert.call_args_list
        assert len(calls) == 2

        # First call should be for user-1 with rateable_user_ids = ["user-2"]
        call1_data = calls[0].args[0]
        assert call1_data["user_id"] == "user-1"
        assert call1_data["rateable_user_ids"] == ["user-2"]

        # Second call should be for user-2 with rateable_user_ids = ["user-1"]
        call2_data = calls[1].args[0]
        assert call2_data["user_id"] == "user-2"
        assert call2_data["rateable_user_ids"] == ["user-1"]

    @pytest.mark.unit
    def test_pending_ratings_expires_in_48_hours(self) -> None:
        """The expires_at is set to ~48 hours from now."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value.data = [{}]
        mock_supabase.table.return_value = mock_table

        participants = [
            {"user_id": "user-1", "participant_type": "human"},
            {"user_id": "user-2", "participant_type": "human"},
        ]

        _create_pending_ratings(mock_supabase, "session-1", participants)

        call_data = mock_table.insert.call_args_list[0].args[0]
        expires_at = datetime.fromisoformat(call_data["expires_at"])
        now = datetime.now(timezone.utc)

        # Should expire in approximately 48 hours (allow 1 minute tolerance)
        delta = expires_at - now
        assert timedelta(hours=47, minutes=59) < delta < timedelta(hours=48, minutes=1)

    @pytest.mark.unit
    def test_no_pending_ratings_for_solo_session(self) -> None:
        """Does not create pending_ratings for sessions with only 1 human."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        participants = [
            {"user_id": "user-1", "participant_type": "human"},
        ]

        count = _create_pending_ratings(mock_supabase, "session-1", participants)

        assert count == 0
        mock_table.insert.assert_not_called()

    @pytest.mark.unit
    def test_excludes_ai_participants(self) -> None:
        """Does not create pending_ratings for AI participants."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value.data = [{}]
        mock_supabase.table.return_value = mock_table

        participants = [
            {"user_id": "user-1", "participant_type": "human"},
            {"user_id": "user-2", "participant_type": "human"},
            {"user_id": None, "participant_type": "ai", "ai_companion_name": "Buddy"},
        ]

        count = _create_pending_ratings(mock_supabase, "session-1", participants)

        assert count == 2
        # Only 2 humans should get pending_ratings
        assert mock_table.insert.call_count == 2

    @pytest.mark.unit
    def test_handles_insert_failure_gracefully(self) -> None:
        """Continues creating records even if one fails."""
        mock_supabase = MagicMock()
        mock_table = MagicMock()
        # First insert succeeds, second fails, third succeeds
        mock_table.insert.return_value.execute.side_effect = [
            MagicMock(data=[{}]),
            Exception("DB error"),
            MagicMock(data=[{}]),
        ]
        mock_supabase.table.return_value = mock_table

        participants = [
            {"user_id": "user-1", "participant_type": "human"},
            {"user_id": "user-2", "participant_type": "human"},
            {"user_id": "user-3", "participant_type": "human"},
        ]

        count = _create_pending_ratings(mock_supabase, "session-1", participants)

        # 2 successful inserts
        assert count == 2
        # 3 insert attempts
        assert mock_table.insert.call_count == 3
