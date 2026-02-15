"""Unit tests for session slot-related endpoints.

Tests:
- get_upcoming_slots() — returns 6 slots with counts and estimates
- quick_match() with target_slot_time — validates target slot
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.auth import AuthUser
from app.models.session import QuickMatchRequest, SessionFilters, TableMode
from app.routers.sessions import get_upcoming_slots, quick_match

# =============================================================================
# Shared Fixtures
# =============================================================================


@pytest.fixture
def auth_user():
    """Standard authenticated user for tests."""
    return AuthUser(auth_id="auth-123", email="test@example.com")


@pytest.fixture
def mock_profile():
    """Mock user profile returned by user_service."""
    profile = MagicMock()
    profile.id = "user-123"
    profile.display_name = "Test User"
    profile.username = "testuser"
    profile.banned_until = None
    return profile


@pytest.fixture
def mock_user_service(mock_profile):
    """Mock UserService that returns the mock profile."""
    service = MagicMock()
    service.get_user_by_auth_id.return_value = mock_profile
    return service


@pytest.fixture
def mock_user_service_no_user():
    """Mock UserService that returns None (user not found)."""
    service = MagicMock()
    service.get_user_by_auth_id.return_value = None
    return service


@pytest.fixture
def mock_session_service():
    """Mock SessionService with slot methods."""
    service = MagicMock()

    # Default slot times (6 slots starting at 14:30)
    base = datetime(2026, 2, 11, 14, 30, 0, tzinfo=timezone.utc)
    slot_times = [base + timedelta(minutes=30 * i) for i in range(6)]
    service.calculate_upcoming_slots.return_value = slot_times

    # Queue counts: 3 at first slot, 0 elsewhere
    service.get_slot_queue_counts.return_value = {
        t.isoformat(): (3 if i == 0 else 0) for i, t in enumerate(slot_times)
    }

    # Estimates: 12 for all
    service.get_slot_estimates.return_value = {t.isoformat(): 12 for t in slot_times}

    # User has no existing sessions
    service.get_user_sessions_at_slots.return_value = set()

    return service


# =============================================================================
# get_upcoming_slots() Tests
# =============================================================================


class TestGetUpcomingSlots:
    """Tests for the GET /upcoming-slots endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_returns_6_slots(
        self, auth_user, mock_user_service, mock_session_service
    ) -> None:
        """Returns 6 time slots with queue counts and estimates."""
        result = await get_upcoming_slots(
            mode=None,
            user=auth_user,
            session_service=mock_session_service,
            user_service=mock_user_service,
        )

        assert len(result.slots) == 6
        mock_session_service.calculate_upcoming_slots.assert_called_once()
        mock_session_service.get_slot_queue_counts.assert_called_once()
        mock_session_service.get_slot_estimates.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_slot_has_queue_count(
        self, auth_user, mock_user_service, mock_session_service
    ) -> None:
        """First slot should have queue_count=3 from mock data."""
        result = await get_upcoming_slots(
            mode=None,
            user=auth_user,
            session_service=mock_session_service,
            user_service=mock_user_service,
        )

        assert result.slots[0].queue_count == 3
        assert result.slots[1].queue_count == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_slot_has_estimated_count(
        self, auth_user, mock_user_service, mock_session_service
    ) -> None:
        """All slots should have estimated_count=12 from mock data."""
        result = await get_upcoming_slots(
            mode=None,
            user=auth_user,
            session_service=mock_session_service,
            user_service=mock_user_service,
        )

        for slot in result.slots:
            assert slot.estimated_count == 12

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_slot_has_user_session_flag(
        self, auth_user, mock_user_service, mock_session_service
    ) -> None:
        """has_user_session should be False when user has no sessions."""
        result = await get_upcoming_slots(
            mode=None,
            user=auth_user,
            session_service=mock_session_service,
            user_service=mock_user_service,
        )

        for slot in result.slots:
            assert slot.has_user_session is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_marks_user_session_as_joined(
        self, auth_user, mock_user_service, mock_session_service
    ) -> None:
        """has_user_session should be True for slots user already joined."""
        # User has session at first slot
        base = datetime(2026, 2, 11, 14, 30, 0, tzinfo=timezone.utc)
        mock_session_service.get_user_sessions_at_slots.return_value = {base.isoformat()}

        result = await get_upcoming_slots(
            mode=None,
            user=auth_user,
            session_service=mock_session_service,
            user_service=mock_user_service,
        )

        assert result.slots[0].has_user_session is True
        assert result.slots[1].has_user_session is False

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_passes_mode_filter(
        self, auth_user, mock_user_service, mock_session_service
    ) -> None:
        """Mode parameter is forwarded to get_slot_queue_counts."""
        await get_upcoming_slots(
            mode="quiet",
            user=auth_user,
            session_service=mock_session_service,
            user_service=mock_user_service,
        )

        mock_session_service.get_slot_queue_counts.assert_called_once()
        call_kwargs = mock_session_service.get_slot_queue_counts.call_args
        assert call_kwargs.kwargs.get("mode") == "quiet"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_user_not_found_raises_404(
        self, auth_user, mock_user_service_no_user, mock_session_service
    ) -> None:
        """Raises 404 when user profile is not found."""
        with pytest.raises(HTTPException) as exc_info:
            await get_upcoming_slots(
                mode=None,
                user=auth_user,
                session_service=mock_session_service,
                user_service=mock_user_service_no_user,
            )
        assert exc_info.value.status_code == 404


# =============================================================================
# quick_match() with target_slot_time Tests
# =============================================================================


class TestQuickMatchWithTargetSlot:
    """Tests for quick_match() with target_slot_time parameter."""

    def _setup_quick_match_mocks(self, mock_session_service, mock_profile):
        """Set up mocks for quick_match dependencies."""
        credit_service = MagicMock()
        credit_service.has_sufficient_credits.return_value = True

        rating_service = MagicMock()
        rating_service.has_pending_ratings.return_value = False

        session_data = {
            "id": "session-abc",
            "start_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.now(timezone.utc) + timedelta(hours=1, minutes=55)).isoformat(),
            "mode": "forced_audio",
            "current_phase": "setup",
            "livekit_room_name": "focus-abc",
            "topic": None,
            "language": "en",
            "participants": [],
            "available_seats": 3,
        }
        mock_session_service.find_or_create_session.return_value = (session_data, 1)
        mock_session_service.get_user_session_at_time.return_value = None
        mock_session_service.generate_livekit_token.return_value = "test-token"

        return credit_service, rating_service

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_uses_target_slot_time(
        self, auth_user, mock_user_service, mock_profile, mock_session_service
    ) -> None:
        """When target_slot_time is provided, it's used instead of calculate_next_slot."""
        credit_service, rating_service = self._setup_quick_match_mocks(
            mock_session_service, mock_profile
        )

        target = datetime.now(timezone.utc) + timedelta(hours=2)
        target = target.replace(minute=0, second=0, microsecond=0)

        match_request = QuickMatchRequest(
            filters=SessionFilters(mode=TableMode.FORCED_AUDIO),
            target_slot_time=target,
        )

        await quick_match(
            request=MagicMock(),
            match_request=match_request,
            user=auth_user,
            session_service=mock_session_service,
            credit_service=credit_service,
            user_service=mock_user_service,
            rating_service=rating_service,
        )

        # Should NOT call calculate_next_slot since target was provided
        mock_session_service.calculate_next_slot.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rejects_past_target_slot(
        self, auth_user, mock_user_service, mock_profile, mock_session_service
    ) -> None:
        """Raises 400 when target_slot_time is in the past."""
        credit_service, rating_service = self._setup_quick_match_mocks(
            mock_session_service, mock_profile
        )

        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        past_time = past_time.replace(minute=0, second=0, microsecond=0)

        match_request = QuickMatchRequest(
            target_slot_time=past_time,
        )

        with pytest.raises(HTTPException) as exc_info:
            await quick_match(
                request=MagicMock(),
                match_request=match_request,
                user=auth_user,
                session_service=mock_session_service,
                credit_service=credit_service,
                user_service=mock_user_service,
                rating_service=rating_service,
            )
        assert exc_info.value.status_code == 400
        assert "future" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rejects_non_30min_boundary(
        self, auth_user, mock_user_service, mock_profile, mock_session_service
    ) -> None:
        """Raises 400 when target_slot_time is not at :00 or :30."""
        credit_service, rating_service = self._setup_quick_match_mocks(
            mock_session_service, mock_profile
        )

        bad_time = datetime.now(timezone.utc) + timedelta(hours=2)
        bad_time = bad_time.replace(minute=15, second=0, microsecond=0)

        match_request = QuickMatchRequest(
            target_slot_time=bad_time,
        )

        with pytest.raises(HTTPException) as exc_info:
            await quick_match(
                request=MagicMock(),
                match_request=match_request,
                user=auth_user,
                session_service=mock_session_service,
                credit_service=credit_service,
                user_service=mock_user_service,
                rating_service=rating_service,
            )
        assert exc_info.value.status_code == 400
        assert ":00 or :30" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_falls_back_to_calculate_next_slot(
        self, auth_user, mock_user_service, mock_profile, mock_session_service
    ) -> None:
        """When target_slot_time is None, calls calculate_next_slot()."""
        credit_service, rating_service = self._setup_quick_match_mocks(
            mock_session_service, mock_profile
        )

        future_slot = datetime.now(timezone.utc) + timedelta(hours=1)
        future_slot = future_slot.replace(minute=0, second=0, microsecond=0)
        mock_session_service.calculate_next_slot.return_value = future_slot

        match_request = QuickMatchRequest(
            target_slot_time=None,
        )

        await quick_match(
            request=MagicMock(),
            match_request=match_request,
            user=auth_user,
            session_service=mock_session_service,
            credit_service=credit_service,
            user_service=mock_user_service,
            rating_service=rating_service,
        )

        mock_session_service.calculate_next_slot.assert_called_once()
