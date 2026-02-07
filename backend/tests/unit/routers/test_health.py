"""Unit tests for health check endpoints.

Tests:
- health_check() basic response
- redis_health_check() success and failure
- livekit_health_check() configured and not configured
- root() welcome message
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.routers.health import health_check, livekit_health_check, redis_health_check, root

# =============================================================================
# health_check() Tests
# =============================================================================


class TestHealthCheck:
    """Tests for the GET /health endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_returns_healthy_status(self) -> None:
        """Returns status healthy with service name."""
        result = await health_check()
        assert result == {"status": "healthy", "service": "focus-squad-api"}

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_status_field_is_healthy(self) -> None:
        """The status field is exactly 'healthy'."""
        result = await health_check()
        assert result["status"] == "healthy"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_service_field_is_correct(self) -> None:
        """The service field identifies focus-squad-api."""
        result = await health_check()
        assert result["service"] == "focus-squad-api"


# =============================================================================
# redis_health_check() Tests
# =============================================================================


class TestRedisHealthCheck:
    """Tests for the GET /health/redis endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("app.routers.health.get_redis")
    async def test_returns_healthy_when_redis_responds(self, mock_get_redis) -> None:
        """Returns healthy status when redis.ping() succeeds."""
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_get_redis.return_value = mock_redis

        result = await redis_health_check()

        assert result == {"status": "healthy", "service": "redis"}
        mock_redis.ping.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("app.routers.health.get_redis")
    async def test_returns_unhealthy_when_redis_raises(self, mock_get_redis) -> None:
        """Returns unhealthy status with error when redis.ping() raises."""
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(side_effect=ConnectionError("Connection refused"))
        mock_get_redis.return_value = mock_redis

        result = await redis_health_check()

        assert result["status"] == "unhealthy"
        assert result["service"] == "redis"
        assert "Connection refused" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("app.routers.health.get_redis")
    async def test_returns_unhealthy_when_get_redis_raises(self, mock_get_redis) -> None:
        """Returns unhealthy status when get_redis() itself raises."""
        mock_get_redis.side_effect = RuntimeError("Redis not initialized")

        result = await redis_health_check()

        assert result["status"] == "unhealthy"
        assert result["service"] == "redis"
        assert "Redis not initialized" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("app.routers.health.get_redis")
    async def test_returns_unhealthy_on_timeout(self, mock_get_redis) -> None:
        """Returns unhealthy status when redis.ping() times out."""
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(side_effect=TimeoutError("Connection timed out"))
        mock_get_redis.return_value = mock_redis

        result = await redis_health_check()

        assert result["status"] == "unhealthy"
        assert result["service"] == "redis"
        assert "timed out" in result["error"]


# =============================================================================
# livekit_health_check() Tests
# =============================================================================


class TestLivekitHealthCheck:
    """Tests for the GET /health/livekit endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("app.services.livekit_service.LiveKitService")
    async def test_returns_configured_when_credentials_set(self, mock_livekit_cls) -> None:
        """Returns configured status when LiveKit credentials are available."""
        mock_instance = MagicMock()
        mock_instance.is_configured = True
        mock_livekit_cls.return_value = mock_instance

        result = await livekit_health_check()

        assert result["status"] == "configured"
        assert result["service"] == "livekit"
        assert "Ready for live audio" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("app.services.livekit_service.LiveKitService")
    async def test_returns_not_configured_when_credentials_missing(self, mock_livekit_cls) -> None:
        """Returns not_configured status when LiveKit credentials are missing."""
        mock_instance = MagicMock()
        mock_instance.is_configured = False
        mock_livekit_cls.return_value = mock_instance

        result = await livekit_health_check()

        assert result["status"] == "not_configured"
        assert result["service"] == "livekit"
        assert "LIVEKIT_API_KEY" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("app.services.livekit_service.LiveKitService")
    async def test_message_mentions_env_vars_when_not_configured(self, mock_livekit_cls) -> None:
        """Error message references all required env vars."""
        mock_instance = MagicMock()
        mock_instance.is_configured = False
        mock_livekit_cls.return_value = mock_instance

        result = await livekit_health_check()

        assert "LIVEKIT_API_KEY" in result["message"]
        assert "LIVEKIT_API_SECRET" in result["message"]
        assert "LIVEKIT_URL" in result["message"]


# =============================================================================
# root() Tests
# =============================================================================


class TestRoot:
    """Tests for the GET / endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_returns_welcome_message(self) -> None:
        """Returns welcome message with docs link."""
        result = await root()
        assert result == {"message": "Welcome to Focus Squad API", "docs": "/docs"}

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_docs_points_to_slash_docs(self) -> None:
        """The docs field points to /docs."""
        result = await root()
        assert result["docs"] == "/docs"
