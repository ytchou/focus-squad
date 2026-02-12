"""Unit tests for SessionService private session methods.

Tests:
- create_private_session: success with partners, no partners, insert failure
- get_pending_invitations: returns active only (filters expired), empty list
- respond_to_invitation: accept success, decline success, not found, expired
- find_matching_session: filters out private sessions via .eq("is_private", False)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.partner import InvitationExpiredError, InvitationNotFoundError
from app.models.session import SessionFilters, SessionPhase, TableMode
from app.services.session_service import SessionService, SessionServiceError

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_supabase():
    """Mock Supabase client with table-specific routing."""
    mock = MagicMock()

    mock_sessions = MagicMock()
    mock_participants = MagicMock()
    mock_invitations = MagicMock()

    def table_router(name):
        routes = {
            "sessions": mock_sessions,
            "session_participants": mock_participants,
            "table_invitations": mock_invitations,
        }
        return routes.get(name, MagicMock())

    mock.table.side_effect = table_router
    return mock, mock_sessions, mock_participants, mock_invitations


@pytest.fixture
def session_service(mock_supabase):
    """SessionService with mocked Supabase."""
    mock, _, _, _ = mock_supabase
    return SessionService(supabase=mock)


# =============================================================================
# Helpers
# =============================================================================

FUTURE_TIME = datetime(2026, 3, 1, 14, 0, 0, tzinfo=timezone.utc)
PAST_TIME = datetime(2026, 1, 1, 14, 0, 0, tzinfo=timezone.utc)


def _make_session_row(
    session_id: str = "session-private-1",
    start_time: datetime = FUTURE_TIME,
    is_private: bool = True,
    max_seats: int = 4,
) -> dict:
    """Create a session record dict as returned from DB."""
    end_time = start_time + timedelta(minutes=55)
    return {
        "id": session_id,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "mode": "forced_audio",
        "topic": "study",
        "language": "en",
        "current_phase": SessionPhase.SETUP.value,
        "phase_started_at": start_time.isoformat(),
        "livekit_room_name": "private-abc123",
        "room_type": "library",
        "is_private": is_private,
        "created_by": "creator-1",
        "max_seats": max_seats,
    }


def _make_invitation_row(
    invitation_id: str = "inv-1",
    session_id: str = "session-private-1",
    inviter_id: str = "creator-1",
    invitee_id: str = "partner-1",
    status: str = "pending",
    session_start: datetime = FUTURE_TIME,
) -> dict:
    """Create an invitation record dict with embedded session data."""
    return {
        "id": invitation_id,
        "session_id": session_id,
        "inviter_id": inviter_id,
        "invitee_id": invitee_id,
        "status": status,
        "created_at": "2026-02-12T10:00:00+00:00",
        "sessions": {
            "id": session_id,
            "start_time": session_start.isoformat(),
            "end_time": (session_start + timedelta(minutes=55)).isoformat(),
            "mode": "forced_audio",
            "topic": "study",
            "max_seats": 4,
        },
    }


# =============================================================================
# Test: create_private_session
# =============================================================================


class TestCreatePrivateSession:
    """Tests for create_private_session() method."""

    @pytest.mark.unit
    def test_success_with_partners(self, session_service, mock_supabase) -> None:
        """Creates session, adds creator as participant, sends invitations."""
        _, mock_sessions, mock_participants, mock_invitations = mock_supabase

        session_row = _make_session_row()
        mock_sessions.insert.return_value.execute.return_value.data = [session_row]
        mock_participants.insert.return_value.execute.return_value.data = [
            {"id": "p-1", "seat_number": 1}
        ]

        invitation_rows = [
            {"id": "inv-1", "invitee_id": "partner-1", "status": "pending"},
            {"id": "inv-2", "invitee_id": "partner-2", "status": "pending"},
        ]
        mock_invitations.insert.return_value.execute.return_value.data = invitation_rows

        result = session_service.create_private_session(
            creator_id="creator-1",
            partner_ids=["partner-1", "partner-2"],
            time_slot=FUTURE_TIME,
            mode="forced_audio",
            max_seats=4,
            fill_ai=True,
            topic="study",
        )

        assert result["session_id"] == "session-private-1"
        assert result["invitations_sent"] == 2

        # Verify session insert data
        session_insert_data = mock_sessions.insert.call_args[0][0]
        assert session_insert_data["is_private"] is True
        assert session_insert_data["created_by"] == "creator-1"
        assert session_insert_data["max_seats"] == 4
        assert session_insert_data["mode"] == "forced_audio"
        assert session_insert_data["topic"] == "study"
        assert session_insert_data["current_phase"] == "setup"
        assert session_insert_data["livekit_room_name"].startswith("private-")

        # Verify creator added as participant at seat 1
        participant_insert_data = mock_participants.insert.call_args[0][0]
        assert participant_insert_data["session_id"] == "session-private-1"
        assert participant_insert_data["user_id"] == "creator-1"
        assert participant_insert_data["participant_type"] == "human"
        assert participant_insert_data["seat_number"] == 1

        # Verify invitations batch insert
        invitations_insert_data = mock_invitations.insert.call_args[0][0]
        assert len(invitations_insert_data) == 2
        assert invitations_insert_data[0]["invitee_id"] == "partner-1"
        assert invitations_insert_data[1]["invitee_id"] == "partner-2"
        assert all(inv["inviter_id"] == "creator-1" for inv in invitations_insert_data)
        assert all(inv["status"] == "pending" for inv in invitations_insert_data)

    @pytest.mark.unit
    def test_success_with_no_partners(self, session_service, mock_supabase) -> None:
        """Creates session with empty partner list; no invitations sent."""
        _, mock_sessions, mock_participants, mock_invitations = mock_supabase

        session_row = _make_session_row()
        mock_sessions.insert.return_value.execute.return_value.data = [session_row]
        mock_participants.insert.return_value.execute.return_value.data = [
            {"id": "p-1", "seat_number": 1}
        ]

        result = session_service.create_private_session(
            creator_id="creator-1",
            partner_ids=[],
            time_slot=FUTURE_TIME,
            mode="quiet",
            max_seats=2,
            fill_ai=False,
            topic=None,
        )

        assert result["session_id"] == "session-private-1"
        assert result["invitations_sent"] == 0

        # Invitations table should NOT be called
        mock_invitations.insert.assert_not_called()

    @pytest.mark.unit
    def test_session_insert_failure_raises(self, session_service, mock_supabase) -> None:
        """Raises SessionServiceError when session insert returns no data."""
        _, mock_sessions, _, _ = mock_supabase

        mock_sessions.insert.return_value.execute.return_value.data = []

        with pytest.raises(SessionServiceError, match="Failed to create private session"):
            session_service.create_private_session(
                creator_id="creator-1",
                partner_ids=["partner-1"],
                time_slot=FUTURE_TIME,
                mode="forced_audio",
                max_seats=4,
                fill_ai=True,
                topic=None,
            )

    @pytest.mark.unit
    def test_invitation_insert_returns_none_data(self, session_service, mock_supabase) -> None:
        """When invitation insert returns None data, invitations_sent is 0."""
        _, mock_sessions, mock_participants, mock_invitations = mock_supabase

        session_row = _make_session_row()
        mock_sessions.insert.return_value.execute.return_value.data = [session_row]
        mock_participants.insert.return_value.execute.return_value.data = [
            {"id": "p-1", "seat_number": 1}
        ]

        mock_invitations.insert.return_value.execute.return_value.data = None

        result = session_service.create_private_session(
            creator_id="creator-1",
            partner_ids=["partner-1"],
            time_slot=FUTURE_TIME,
            mode="forced_audio",
            max_seats=4,
            fill_ai=True,
            topic=None,
        )

        assert result["invitations_sent"] == 0


# =============================================================================
# Test: get_pending_invitations
# =============================================================================


class TestGetPendingInvitations:
    """Tests for get_pending_invitations() method."""

    @pytest.mark.unit
    def test_returns_active_invitations_only(self, session_service, mock_supabase) -> None:
        """Filters out invitations for sessions that have already started."""
        _, _, _, mock_invitations = mock_supabase

        future_inv = _make_invitation_row(
            invitation_id="inv-future",
            session_start=FUTURE_TIME,
        )
        past_inv = _make_invitation_row(
            invitation_id="inv-past",
            session_start=PAST_TIME,
        )

        (
            mock_invitations.select.return_value.eq.return_value.eq.return_value.execute.return_value
        ).data = [future_inv, past_inv]

        result = session_service.get_pending_invitations("partner-1")

        assert len(result) == 1
        assert result[0]["id"] == "inv-future"

    @pytest.mark.unit
    def test_returns_empty_when_no_invitations(self, session_service, mock_supabase) -> None:
        """Returns empty list when query returns no data."""
        _, _, _, mock_invitations = mock_supabase

        (
            mock_invitations.select.return_value.eq.return_value.eq.return_value.execute.return_value
        ).data = []

        result = session_service.get_pending_invitations("partner-1")

        assert result == []

    @pytest.mark.unit
    def test_returns_empty_when_data_is_none(self, session_service, mock_supabase) -> None:
        """Returns empty list when query returns None data."""
        _, _, _, mock_invitations = mock_supabase

        (
            mock_invitations.select.return_value.eq.return_value.eq.return_value.execute.return_value
        ).data = None

        result = session_service.get_pending_invitations("partner-1")

        assert result == []

    @pytest.mark.unit
    def test_skips_invitations_without_session_data(self, session_service, mock_supabase) -> None:
        """Invitations with missing or empty session join are skipped."""
        _, _, _, mock_invitations = mock_supabase

        inv_no_session = {
            "id": "inv-no-session",
            "session_id": "session-1",
            "inviter_id": "creator-1",
            "invitee_id": "partner-1",
            "status": "pending",
            "sessions": {},
        }

        (
            mock_invitations.select.return_value.eq.return_value.eq.return_value.execute.return_value
        ).data = [inv_no_session]

        result = session_service.get_pending_invitations("partner-1")

        assert result == []


# =============================================================================
# Test: respond_to_invitation
# =============================================================================


class TestRespondToInvitation:
    """Tests for respond_to_invitation() method."""

    @pytest.mark.unit
    def test_accept_success(self, session_service, mock_supabase) -> None:
        """Accept invitation: adds participant and updates status to accepted."""
        _, _, _, mock_invitations = mock_supabase

        invitation = _make_invitation_row(
            invitation_id="inv-1",
            session_start=FUTURE_TIME,
        )

        (
            mock_invitations.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value
        ).data = [invitation]

        updated_inv = {
            **invitation,
            "status": "accepted",
            "responded_at": "2026-02-12T12:00:00+00:00",
        }
        (mock_invitations.update.return_value.eq.return_value.execute.return_value).data = [
            updated_inv
        ]

        with patch.object(session_service, "add_participant") as mock_add:
            mock_add.return_value = {"id": "p-2", "seat_number": 2, "already_active": False}

            result = session_service.respond_to_invitation("inv-1", "partner-1", accept=True)

        mock_add.assert_called_once_with("session-private-1", "partner-1")
        assert result["status"] == "accepted"

    @pytest.mark.unit
    def test_decline_success(self, session_service, mock_supabase) -> None:
        """Decline invitation: updates status without adding participant."""
        _, _, _, mock_invitations = mock_supabase

        invitation = _make_invitation_row(
            invitation_id="inv-1",
            session_start=FUTURE_TIME,
        )

        (
            mock_invitations.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value
        ).data = [invitation]

        updated_inv = {
            **invitation,
            "status": "declined",
            "responded_at": "2026-02-12T12:00:00+00:00",
        }
        (mock_invitations.update.return_value.eq.return_value.execute.return_value).data = [
            updated_inv
        ]

        with patch.object(session_service, "add_participant") as mock_add:
            result = session_service.respond_to_invitation("inv-1", "partner-1", accept=False)

        mock_add.assert_not_called()
        assert result["status"] == "declined"

    @pytest.mark.unit
    def test_not_found_raises(self, session_service, mock_supabase) -> None:
        """Raises InvitationNotFoundError when no matching invitation exists."""
        _, _, _, mock_invitations = mock_supabase

        (
            mock_invitations.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value
        ).data = []

        with pytest.raises(InvitationNotFoundError):
            session_service.respond_to_invitation("bad-id", "partner-1", accept=True)

    @pytest.mark.unit
    def test_expired_raises_on_accept(self, session_service, mock_supabase) -> None:
        """Raises InvitationExpiredError when accepting an invitation for a past session."""
        _, _, _, mock_invitations = mock_supabase

        invitation = _make_invitation_row(
            invitation_id="inv-expired",
            session_start=PAST_TIME,
        )

        (
            mock_invitations.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value
        ).data = [invitation]

        with pytest.raises(InvitationExpiredError):
            session_service.respond_to_invitation("inv-expired", "partner-1", accept=True)

    @pytest.mark.unit
    def test_update_returns_no_data_falls_back(self, session_service, mock_supabase) -> None:
        """When update returns empty data, returns fallback dict with status."""
        _, _, _, mock_invitations = mock_supabase

        invitation = _make_invitation_row(
            invitation_id="inv-1",
            session_start=FUTURE_TIME,
        )

        (
            mock_invitations.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value
        ).data = [invitation]

        (mock_invitations.update.return_value.eq.return_value.execute.return_value).data = []

        with patch.object(session_service, "add_participant"):
            result = session_service.respond_to_invitation("inv-1", "partner-1", accept=True)

        assert result == {"status": "accepted"}


# =============================================================================
# Test: find_matching_session excludes private sessions
# =============================================================================


class TestFindMatchingSessionExcludesPrivate:
    """Tests that find_matching_session includes .eq('is_private', False)."""

    @pytest.mark.unit
    def test_query_calls_eq_is_private_false(self, session_service, mock_supabase) -> None:
        """Verify the query chain includes .eq('is_private', False)."""
        _, mock_sessions, _, _ = mock_supabase

        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.lt.return_value = mock_query
        mock_query.execute.return_value.data = []
        mock_sessions.select.return_value = mock_query

        filters = SessionFilters(mode=TableMode.FORCED_AUDIO)
        start_time = datetime(2026, 2, 5, 14, 30, tzinfo=timezone.utc)

        session_service.find_matching_session(filters, start_time)

        # Collect all .eq() calls to verify is_private=False was included
        eq_calls = mock_query.eq.call_args_list
        eq_call_args = [(call.args if call.args else call[0]) for call in eq_calls]

        found_is_private = False
        for args in eq_call_args:
            if len(args) >= 2 and args[0] == "is_private" and args[1] is False:
                found_is_private = True
                break

        assert found_is_private, (
            f"Expected .eq('is_private', False) in query chain, "
            f"but eq() was called with: {eq_call_args}"
        )

    @pytest.mark.unit
    def test_private_sessions_not_returned(self, session_service, mock_supabase) -> None:
        """Public matching returns None when only private sessions exist (filtered by DB)."""
        _, mock_sessions, _, _ = mock_supabase

        # Simulate DB returning nothing because is_private=False filter excluded them
        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.lt.return_value = mock_query
        mock_query.execute.return_value.data = []
        mock_sessions.select.return_value = mock_query

        filters = SessionFilters()
        start_time = datetime(2026, 2, 5, 14, 30, tzinfo=timezone.utc)

        result = session_service.find_matching_session(filters, start_time)

        assert result is None
