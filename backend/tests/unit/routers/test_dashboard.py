"""Unit tests for the dashboard init batch endpoint."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.models.gamification import WeeklyStreakResponse
from app.models.rating import PendingRatingInfo
from app.routers.dashboard import DashboardInitResponse, dashboard_init

# =============================================================================
# Shared Fixtures
# =============================================================================


@pytest.fixture
def auth_user():
    return AuthUser(auth_id="auth-123", email="test@example.com")


@pytest.fixture
def mock_profile():
    profile = MagicMock()
    profile.id = "user-123"
    profile.display_name = "Test User"
    profile.username = "testuser"
    return profile


@pytest.fixture
def mock_user_service(mock_profile):
    service = MagicMock()
    service.get_user_by_auth_id.return_value = mock_profile
    return service


@pytest.fixture
def mock_rating_service():
    service = MagicMock()
    service.get_pending_ratings.return_value = None
    return service


@pytest.fixture
def mock_session_service():
    service = MagicMock()
    now = datetime.now(timezone.utc)
    slots = [now + timedelta(minutes=30 * i) for i in range(6)]
    service.calculate_upcoming_slots.return_value = slots
    service.get_slot_queue_counts.return_value = {}
    service.get_slot_estimates.return_value = {}
    service.get_user_sessions_at_slots.return_value = set()
    service.get_pending_invitations.return_value = []
    return service


@pytest.fixture
def mock_streak_service():
    service = MagicMock()
    service.get_weekly_streak.return_value = WeeklyStreakResponse(
        session_count=2,
        week_start=date.today(),
        next_bonus_at=3,
        bonus_3_awarded=False,
        bonus_5_awarded=False,
        total_bonus_earned=0,
    )
    return service


# =============================================================================
# Tests
# =============================================================================


class TestDashboardInit:
    """Tests for the dashboard_init() endpoint."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_happy_path_returns_all_sections(
        self,
        auth_user,
        mock_user_service,
        mock_rating_service,
        mock_session_service,
        mock_streak_service,
    ):
        """Successful init returns all dashboard sections."""
        result = await dashboard_init(
            request=MagicMock(),
            mode=None,
            user=auth_user,
            user_service=mock_user_service,
            rating_service=mock_rating_service,
            session_service=mock_session_service,
            streak_service=mock_streak_service,
        )

        assert isinstance(result, DashboardInitResponse)
        assert result.pending_ratings.has_pending is False
        assert result.pending_ratings.pending is None
        assert result.invitations == []
        assert result.streak.session_count == 2
        assert len(result.upcoming_slots.slots) == 6

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_not_found_returns_404(
        self,
        auth_user,
        mock_rating_service,
        mock_session_service,
        mock_streak_service,
    ):
        """Missing user raises 404."""
        user_service = MagicMock()
        user_service.get_user_by_auth_id.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await dashboard_init(
                request=MagicMock(),
                mode=None,
                user=auth_user,
                user_service=user_service,
                rating_service=mock_rating_service,
                session_service=mock_session_service,
                streak_service=mock_streak_service,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pending_ratings_included(
        self,
        auth_user,
        mock_user_service,
        mock_session_service,
        mock_streak_service,
    ):
        """Pending ratings are properly included in response."""
        rating_service = MagicMock()
        rating_service.get_pending_ratings.return_value = PendingRatingInfo(
            session_id="session-abc",
            rateable_users=[],
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )

        result = await dashboard_init(
            request=MagicMock(),
            mode=None,
            user=auth_user,
            user_service=mock_user_service,
            rating_service=rating_service,
            session_service=mock_session_service,
            streak_service=mock_streak_service,
        )

        assert result.pending_ratings.has_pending is True
        assert result.pending_ratings.pending.session_id == "session-abc"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invitations_included(
        self,
        auth_user,
        mock_user_service,
        mock_rating_service,
        mock_streak_service,
    ):
        """Invitations are transformed and included."""
        session_service = MagicMock()
        now = datetime.now(timezone.utc)
        slots = [now + timedelta(minutes=30 * i) for i in range(6)]
        session_service.calculate_upcoming_slots.return_value = slots
        session_service.get_slot_queue_counts.return_value = {}
        session_service.get_slot_estimates.return_value = {}
        session_service.get_user_sessions_at_slots.return_value = set()
        session_service.get_pending_invitations.return_value = [
            {
                "id": "inv-1",
                "session_id": "session-xyz",
                "inviter_id": "inviter-1",
                "status": "pending",
                "created_at": now.isoformat(),
                "sessions": {
                    "start_time": (now + timedelta(hours=1)).isoformat(),
                    "mode": "quiet",
                    "topic": "Study group",
                },
            }
        ]

        # Mock user_service to return inviter profile
        user_service = MagicMock()
        profile = MagicMock()
        profile.id = "user-123"
        user_service.get_user_by_auth_id.return_value = profile

        inviter = MagicMock()
        inviter.display_name = "Inviter"
        inviter.username = "inviter1"
        user_service.get_public_profile.return_value = inviter

        result = await dashboard_init(
            request=MagicMock(),
            mode=None,
            user=auth_user,
            user_service=user_service,
            rating_service=mock_rating_service,
            session_service=session_service,
            streak_service=mock_streak_service,
        )

        assert len(result.invitations) == 1
        assert result.invitations[0].session_id == "session-xyz"
        assert result.invitations[0].inviter_name == "Inviter"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mode_filter_passed_to_slots(
        self,
        auth_user,
        mock_user_service,
        mock_rating_service,
        mock_session_service,
        mock_streak_service,
    ):
        """Mode query parameter is passed through to slot query."""
        await dashboard_init(
            request=MagicMock(),
            mode="quiet",
            user=auth_user,
            user_service=mock_user_service,
            rating_service=mock_rating_service,
            session_service=mock_session_service,
            streak_service=mock_streak_service,
        )

        mock_session_service.get_slot_queue_counts.assert_called_once()
        call_args = mock_session_service.get_slot_queue_counts.call_args
        assert (
            call_args[1].get("mode") == "quiet" or call_args[0][1] == "quiet"
            if len(call_args[0]) > 1
            else call_args[1].get("mode") == "quiet"
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_service_exception_propagates(
        self,
        auth_user,
        mock_user_service,
        mock_session_service,
        mock_streak_service,
    ):
        """Exception in any service propagates."""
        rating_service = MagicMock()
        rating_service.get_pending_ratings.side_effect = Exception("DB error")

        with pytest.raises(Exception, match="DB error"):
            await dashboard_init(
                request=MagicMock(),
                mode=None,
                user=auth_user,
                user_service=mock_user_service,
                rating_service=rating_service,
                session_service=mock_session_service,
                streak_service=mock_streak_service,
            )
