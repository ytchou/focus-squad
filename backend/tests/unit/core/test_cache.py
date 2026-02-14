"""Unit tests for app-level Redis cache utility.

Tests:
- cache_get: hit, miss, deserialization, error handling
- cache_set: serialization, TTL, error handling
- cache_delete: single key deletion, error handling
- cache_delete_pattern: SCAN-based glob deletion, error handling
- _get_cache_client: lazy init + singleton
- reset_cache_client: clears singleton
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_cache_module():
    """Reset the global _sync_redis before each test."""
    import app.core.cache as cache_mod

    cache_mod._sync_redis = None
    yield
    cache_mod._sync_redis = None


@pytest.fixture()
def mock_redis():
    """Provide a MagicMock Redis client and patch _get_cache_client."""
    client = MagicMock()
    with patch("app.core.cache._get_cache_client", return_value=client):
        yield client


# =============================================================================
# cache_get() Tests
# =============================================================================


class TestCacheGet:
    @pytest.mark.unit
    def test_returns_deserialized_value(self, mock_redis: MagicMock) -> None:
        """Returns Python object from JSON-stored value."""
        mock_redis.get.return_value = '{"balance": 5}'

        from app.core.cache import cache_get

        result = cache_get("credits:user-1")

        assert result == {"balance": 5}
        mock_redis.get.assert_called_once_with("credits:user-1")

    @pytest.mark.unit
    def test_returns_none_on_miss(self, mock_redis: MagicMock) -> None:
        """Returns None when key does not exist in cache."""
        mock_redis.get.return_value = None

        from app.core.cache import cache_get

        result = cache_get("nonexistent")

        assert result is None

    @pytest.mark.unit
    def test_returns_none_on_error(self, mock_redis: MagicMock) -> None:
        """Returns None (not raises) when Redis throws."""
        mock_redis.get.side_effect = ConnectionError("Redis down")

        from app.core.cache import cache_get

        result = cache_get("some-key")

        assert result is None


# =============================================================================
# cache_set() Tests
# =============================================================================


class TestCacheSet:
    @pytest.mark.unit
    def test_stores_json_with_ttl(self, mock_redis: MagicMock) -> None:
        """Serializes value to JSON and sets with TTL."""
        from app.core.cache import cache_set

        cache_set("credits:user-1", {"balance": 5}, ttl=30)

        mock_redis.set.assert_called_once_with("credits:user-1", '{"balance": 5}', ex=30)

    @pytest.mark.unit
    def test_default_ttl_60(self, mock_redis: MagicMock) -> None:
        """Uses 60-second TTL by default."""
        from app.core.cache import cache_set

        cache_set("key", "value")

        _, kwargs = mock_redis.set.call_args
        assert kwargs["ex"] == 60

    @pytest.mark.unit
    def test_silently_handles_error(self, mock_redis: MagicMock) -> None:
        """Does not raise when Redis throws."""
        mock_redis.set.side_effect = ConnectionError("Redis down")

        from app.core.cache import cache_set

        cache_set("key", "value")  # Should not raise


# =============================================================================
# cache_delete() Tests
# =============================================================================


class TestCacheDelete:
    @pytest.mark.unit
    def test_deletes_key(self, mock_redis: MagicMock) -> None:
        """Calls Redis DELETE on the key."""
        from app.core.cache import cache_delete

        cache_delete("credits:user-1")

        mock_redis.delete.assert_called_once_with("credits:user-1")

    @pytest.mark.unit
    def test_silently_handles_error(self, mock_redis: MagicMock) -> None:
        """Does not raise when Redis throws."""
        mock_redis.delete.side_effect = ConnectionError("Redis down")

        from app.core.cache import cache_delete

        cache_delete("some-key")  # Should not raise


# =============================================================================
# cache_delete_pattern() Tests
# =============================================================================


class TestCacheDeletePattern:
    @pytest.mark.unit
    def test_scans_and_deletes_matching_keys(self, mock_redis: MagicMock) -> None:
        """Uses SCAN to find matching keys, then DELETEs them."""
        mock_redis.scan.side_effect = [
            (42, ["slot_counts:focus:abc", "slot_counts:focus:def"]),
            (0, ["slot_counts:quiet:ghi"]),
        ]

        from app.core.cache import cache_delete_pattern

        cache_delete_pattern("slot_counts:*")

        assert mock_redis.scan.call_count == 2
        assert mock_redis.delete.call_count == 2
        mock_redis.delete.assert_any_call("slot_counts:focus:abc", "slot_counts:focus:def")
        mock_redis.delete.assert_any_call("slot_counts:quiet:ghi")

    @pytest.mark.unit
    def test_no_keys_matched(self, mock_redis: MagicMock) -> None:
        """Does not call DELETE when no keys match the pattern."""
        mock_redis.scan.return_value = (0, [])

        from app.core.cache import cache_delete_pattern

        cache_delete_pattern("nonexistent:*")

        mock_redis.delete.assert_not_called()

    @pytest.mark.unit
    def test_silently_handles_error(self, mock_redis: MagicMock) -> None:
        """Does not raise when Redis throws."""
        mock_redis.scan.side_effect = ConnectionError("Redis down")

        from app.core.cache import cache_delete_pattern

        cache_delete_pattern("slot_counts:*")  # Should not raise


# =============================================================================
# _get_cache_client() + reset_cache_client() Tests
# =============================================================================


class TestCacheClient:
    @pytest.mark.unit
    def test_lazy_init_singleton(self) -> None:
        """Creates Redis client on first call, reuses on second."""
        mock_client = MagicMock()

        with patch("app.core.cache.SyncRedis") as MockRedis:
            MockRedis.from_url.return_value = mock_client

            with patch("app.core.cache.get_settings") as mock_settings:
                mock_settings.return_value.redis_url = "redis://localhost:6379"

                from app.core.cache import _get_cache_client

                first = _get_cache_client()
                second = _get_cache_client()

        assert first is second
        assert MockRedis.from_url.call_count == 1

    @pytest.mark.unit
    def test_reset_clears_singleton(self) -> None:
        """reset_cache_client() forces next call to create a new client."""
        import app.core.cache as cache_mod

        cache_mod._sync_redis = MagicMock()

        from app.core.cache import reset_cache_client

        reset_cache_client()

        assert cache_mod._sync_redis is None
