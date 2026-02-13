"""Tests for Redis connection validation with retry."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError


@pytest.fixture(autouse=True)
def reset_redis_after_test():
    """Reset Redis state after each test to prevent pollution."""
    yield
    # Cleanup after test
    from app.core.redis import _reset_redis

    _reset_redis()


class TestRedisInitWithRetry:
    """Test Redis initialization with connection validation and retry."""

    @pytest.mark.asyncio
    async def test_successful_ping_on_first_try(self):
        """Successful ping on first attempt proceeds without retry."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)

        with patch("app.core.redis.Redis", return_value=mock_redis):
            with patch("app.core.redis.ConnectionPool") as mock_pool:
                mock_pool.from_url = MagicMock()

                from app.core.redis import _reset_redis, init_redis

                _reset_redis()  # Clear any existing state
                await init_redis()

                mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_success_on_second_retry(self):
        """Success on retry 2 logs warning and continues."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=[RedisConnectionError("Connection refused"), True])

        with patch("app.core.redis.Redis", return_value=mock_redis):
            with patch("app.core.redis.ConnectionPool") as mock_pool:
                mock_pool.from_url = MagicMock()
                with patch("app.core.redis.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                    with patch("app.core.redis.logger") as mock_logger:
                        from app.core.redis import _reset_redis, init_redis

                        _reset_redis()
                        await init_redis()

                        assert mock_redis.ping.call_count == 2
                        mock_sleep.assert_called_once_with(1)  # First retry delay
                        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_failure_after_three_attempts(self):
        """Failure after 3 attempts raises RuntimeError."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=RedisConnectionError("Connection refused"))

        with patch("app.core.redis.Redis", return_value=mock_redis):
            with patch("app.core.redis.ConnectionPool") as mock_pool:
                mock_pool.from_url = MagicMock()
                with patch("app.core.redis.asyncio.sleep", new_callable=AsyncMock):
                    from app.core.redis import _reset_redis, init_redis

                    _reset_redis()

                    with pytest.raises(RuntimeError) as exc_info:
                        await init_redis()

                    assert "Redis connection failed after 3 attempts" in str(exc_info.value)
                    assert mock_redis.ping.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_delays_are_exponential(self):
        """Retry delays follow exponential backoff (1s, 2s, 4s)."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=RedisConnectionError("Connection refused"))

        with patch("app.core.redis.Redis", return_value=mock_redis):
            with patch("app.core.redis.ConnectionPool") as mock_pool:
                mock_pool.from_url = MagicMock()
                with patch("app.core.redis.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                    from app.core.redis import _reset_redis, init_redis

                    _reset_redis()

                    with pytest.raises(RuntimeError):
                        await init_redis()

                    # Should have slept twice (before retry 2 and retry 3)
                    assert mock_sleep.call_count == 2
                    mock_sleep.assert_any_call(1)  # Before attempt 2
                    mock_sleep.assert_any_call(2)  # Before attempt 3

    @pytest.mark.asyncio
    async def test_timeout_error_triggers_retry(self):
        """TimeoutError is caught and triggers retry."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=[asyncio.TimeoutError("Timed out"), True])

        with patch("app.core.redis.Redis", return_value=mock_redis):
            with patch("app.core.redis.ConnectionPool") as mock_pool:
                mock_pool.from_url = MagicMock()
                with patch("app.core.redis.asyncio.sleep", new_callable=AsyncMock):
                    from app.core.redis import _reset_redis, init_redis

                    _reset_redis()
                    await init_redis()

                    assert mock_redis.ping.call_count == 2

    @pytest.mark.asyncio
    async def test_oserror_triggers_retry(self):
        """OSError (network issues) is caught and triggers retry."""
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=[OSError("Network unreachable"), True])

        with patch("app.core.redis.Redis", return_value=mock_redis):
            with patch("app.core.redis.ConnectionPool") as mock_pool:
                mock_pool.from_url = MagicMock()
                with patch("app.core.redis.asyncio.sleep", new_callable=AsyncMock):
                    from app.core.redis import _reset_redis, init_redis

                    _reset_redis()
                    await init_redis()

                    assert mock_redis.ping.call_count == 2
