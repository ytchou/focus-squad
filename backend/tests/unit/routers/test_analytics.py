"""Unit tests for analytics router.

Tests:
- POST /track (track_event) - fire-and-forget analytics tracking
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.auth import AuthUser
from app.routers.analytics import TrackEventRequest, track_event

# =============================================================================
# track_event() Tests
# =============================================================================


class TestTrackEvent:
    """Tests for the track_event() endpoint."""

    @pytest.fixture
    def mock_user(self):
        """Authenticated user context."""
        return AuthUser(auth_id="auth-123", email="test@example.com")

    @pytest.fixture
    def mock_analytics_service(self):
        """AnalyticsService with async track_event method."""
        service = MagicMock()
        service.track_event = AsyncMock()
        return service

    @pytest.fixture
    def mock_user_service(self):
        """UserService with get_user_by_auth_id method."""
        service = MagicMock()
        profile = MagicMock()
        profile.id = "user-456"
        service.get_user_by_auth_id.return_value = profile
        return service

    @pytest.fixture
    def track_request(self):
        """Standard track event request."""
        return TrackEventRequest(
            event_type="session_joined_from_waiting_room",
            session_id=uuid.uuid4(),
            metadata={"source": "waiting_room"},
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_happy_path_profile_found_tracking_succeeds(
        self, mock_user, mock_analytics_service, mock_user_service, track_request
    ) -> None:
        """Profile found and tracking succeeds returns success=True."""
        result = await track_event(
            request=track_request,
            user=mock_user,
            analytics_service=mock_analytics_service,
            user_service=mock_user_service,
        )

        assert result.success is True
        mock_user_service.get_user_by_auth_id.assert_called_once_with(mock_user.auth_id)
        mock_analytics_service.track_event.assert_called_once_with(
            user_id="user-456",
            session_id=track_request.session_id,
            event_type=track_request.event_type,
            metadata=track_request.metadata,
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_profile_not_found_returns_success(
        self, mock_user, mock_analytics_service, mock_user_service, track_request
    ) -> None:
        """When user profile is not found, still returns success=True."""
        mock_user_service.get_user_by_auth_id.return_value = None

        result = await track_event(
            request=track_request,
            user=mock_user,
            analytics_service=mock_analytics_service,
            user_service=mock_user_service,
        )

        assert result.success is True
        mock_user_service.get_user_by_auth_id.assert_called_once_with(mock_user.auth_id)
        mock_analytics_service.track_event.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analytics_service_raises_returns_success(
        self, mock_user, mock_analytics_service, mock_user_service, track_request
    ) -> None:
        """When analytics_service.track_event raises, still returns success=True."""
        mock_analytics_service.track_event.side_effect = Exception("Tracking failed")

        result = await track_event(
            request=track_request,
            user=mock_user,
            analytics_service=mock_analytics_service,
            user_service=mock_user_service,
        )

        assert result.success is True
        mock_analytics_service.track_event.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_service_raises_returns_success(
        self, mock_user, mock_analytics_service, mock_user_service, track_request
    ) -> None:
        """When user_service.get_user_by_auth_id raises, still returns success=True."""
        mock_user_service.get_user_by_auth_id.side_effect = Exception("DB connection lost")

        result = await track_event(
            request=track_request,
            user=mock_user,
            analytics_service=mock_analytics_service,
            user_service=mock_user_service,
        )

        assert result.success is True
        mock_analytics_service.track_event.assert_not_called()
