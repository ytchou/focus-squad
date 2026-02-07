"""Unit tests for LiveKitService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.session import TableMode
from app.services.livekit_service import LiveKitService


@pytest.fixture
def dev_settings():
    """Settings with placeholder LiveKit credentials."""
    mock = MagicMock()
    mock.livekit_api_key = "your-livekit-api-key"
    mock.livekit_api_secret = "your-livekit-api-secret"
    mock.livekit_url = ""
    return mock


@pytest.fixture
def configured_settings():
    """Settings with real LiveKit credentials."""
    mock = MagicMock()
    mock.livekit_api_key = "real-api-key"
    mock.livekit_api_secret = "real-api-secret"
    mock.livekit_url = "wss://livekit.example.com"
    return mock


@pytest.mark.unit
class TestIsConfigured:
    """Tests for LiveKitService.is_configured property."""

    def test_is_configured_true(self, configured_settings):
        """All settings present and real. Returns True."""
        with patch(
            "app.services.livekit_service.get_settings",
            return_value=configured_settings,
        ):
            service = LiveKitService()
            assert service.is_configured is True

    def test_is_configured_false_placeholder(self, dev_settings):
        """livekit_api_key is the placeholder value. Returns False."""
        with patch(
            "app.services.livekit_service.get_settings",
            return_value=dev_settings,
        ):
            service = LiveKitService()
            assert service.is_configured is False


@pytest.mark.unit
class TestCreateRoom:
    """Tests for LiveKitService.create_room."""

    @pytest.mark.asyncio
    async def test_create_room_dev_mode(self, dev_settings):
        """Not configured. Returns mock dict with name, sid=f'dev-{name}', mode."""
        with patch(
            "app.services.livekit_service.get_settings",
            return_value=dev_settings,
        ):
            service = LiveKitService()
            result = await service.create_room("focus-abc")

            assert result["name"] == "focus-abc"
            assert result["sid"] == "dev-focus-abc"
            assert result["creation_time"] == 0
            assert result["mode"] == TableMode.FORCED_AUDIO.value

    @pytest.mark.asyncio
    async def test_create_room_configured(self, configured_settings):
        """Configured. Mock LiveKitAPI and room.create_room. Returns room info."""
        with patch(
            "app.services.livekit_service.get_settings",
            return_value=configured_settings,
        ):
            service = LiveKitService()

            mock_room = MagicMock()
            mock_room.name = "focus-abc"
            mock_room.sid = "RM_123"
            mock_room.creation_time = 12345

            with patch("app.services.livekit_service.api.LiveKitAPI") as MockAPI:
                mock_api = MockAPI.return_value
                mock_api.room.create_room = AsyncMock(return_value=mock_room)

                result = await service.create_room("focus-abc", mode=TableMode.FORCED_AUDIO)

                assert result["name"] == "focus-abc"
                assert result["sid"] == "RM_123"
                assert result["creation_time"] == 12345
                assert result["mode"] == TableMode.FORCED_AUDIO.value


@pytest.mark.unit
class TestDeleteRoom:
    """Tests for LiveKitService.delete_room."""

    @pytest.mark.asyncio
    async def test_delete_room_dev_mode(self, dev_settings):
        """Not configured. Returns True (no-op)."""
        with patch(
            "app.services.livekit_service.get_settings",
            return_value=dev_settings,
        ):
            service = LiveKitService()
            result = await service.delete_room("focus-abc")
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_room_configured(self, configured_settings):
        """Configured. Mock API. Returns True."""
        with patch(
            "app.services.livekit_service.get_settings",
            return_value=configured_settings,
        ):
            service = LiveKitService()

            with patch("app.services.livekit_service.api.LiveKitAPI") as MockAPI:
                mock_api = MockAPI.return_value
                mock_api.room.delete_room = AsyncMock(return_value=None)

                result = await service.delete_room("focus-abc")

                assert result is True
                mock_api.room.delete_room.assert_called_once()


@pytest.mark.unit
class TestGetRoom:
    """Tests for LiveKitService.get_room."""

    @pytest.mark.asyncio
    async def test_get_room_dev_mode(self, dev_settings):
        """Not configured. Returns None."""
        with patch(
            "app.services.livekit_service.get_settings",
            return_value=dev_settings,
        ):
            service = LiveKitService()
            result = await service.get_room("focus-abc")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_room_found(self, configured_settings):
        """Configured. Mock list_rooms returns room. Returns dict."""
        with patch(
            "app.services.livekit_service.get_settings",
            return_value=configured_settings,
        ):
            service = LiveKitService()

            mock_room = MagicMock()
            mock_room.name = "focus-abc"
            mock_room.sid = "RM_456"
            mock_room.num_participants = 3
            mock_room.creation_time = 99999

            mock_response = MagicMock()
            mock_response.rooms = [mock_room]

            with patch("app.services.livekit_service.api.LiveKitAPI") as MockAPI:
                mock_api = MockAPI.return_value
                mock_api.room.list_rooms = AsyncMock(return_value=mock_response)

                result = await service.get_room("focus-abc")

                assert result is not None
                assert result["name"] == "focus-abc"
                assert result["sid"] == "RM_456"
                assert result["num_participants"] == 3
                assert result["creation_time"] == 99999


@pytest.mark.unit
class TestGenerateToken:
    """Tests for LiveKitService.generate_token."""

    def test_generate_token_dev_mode(self, dev_settings):
        """Not configured. Returns 'dev-placeholder-token'."""
        with patch(
            "app.services.livekit_service.get_settings",
            return_value=dev_settings,
        ):
            service = LiveKitService()
            result = service.generate_token("room-1", "user-1", "User 1")
            assert result == "dev-placeholder-token"

    def test_generate_token_forced_audio(self, configured_settings):
        """Mode is FORCED_AUDIO. Verify can_publish=True in grants."""
        with patch(
            "app.services.livekit_service.get_settings",
            return_value=configured_settings,
        ):
            with patch("app.services.livekit_service.api.AccessToken") as MockToken:
                mock_token = MockToken.return_value
                mock_token.to_jwt.return_value = "jwt-token-forced"

                service = LiveKitService()
                result = service.generate_token(
                    "room-1", "user-1", "User 1", mode=TableMode.FORCED_AUDIO
                )

                assert result == "jwt-token-forced"
                mock_token.with_grants.assert_called_once()
                grants = mock_token.with_grants.call_args[0][0]
                assert grants.can_publish is True
                assert grants.room_join is True
                assert grants.room == "room-1"
                assert grants.can_publish_data is True
                assert grants.can_subscribe is True

    def test_generate_token_quiet_mode(self, configured_settings):
        """Mode is QUIET. Verify can_publish=False in grants."""
        with patch(
            "app.services.livekit_service.get_settings",
            return_value=configured_settings,
        ):
            with patch("app.services.livekit_service.api.AccessToken") as MockToken:
                mock_token = MockToken.return_value
                mock_token.to_jwt.return_value = "jwt-token-quiet"

                service = LiveKitService()
                result = service.generate_token("room-1", "user-1", "User 1", mode=TableMode.QUIET)

                assert result == "jwt-token-quiet"
                mock_token.with_grants.assert_called_once()
                grants = mock_token.with_grants.call_args[0][0]
                assert grants.can_publish is False


@pytest.mark.unit
class TestClose:
    """Tests for LiveKitService.close."""

    @pytest.mark.asyncio
    async def test_close_clears_api(self, configured_settings):
        """Set _api to a mock, call close(). Verify _api is None."""
        with patch(
            "app.services.livekit_service.get_settings",
            return_value=configured_settings,
        ):
            service = LiveKitService()

            mock_api = MagicMock()
            mock_api.aclose = AsyncMock(return_value=None)
            service._api = mock_api

            await service.close()

            assert service._api is None
            mock_api.aclose.assert_called_once()
