"""Tests for JWKS cache with TTL and background refresh."""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest


class TestJWKSCache:
    """Test JWKS caching with TTL and background refresh."""

    @pytest.mark.asyncio
    async def test_fresh_cache_returns_without_fetch(self):
        """Fresh cache returns keys without network fetch."""
        from app.core.auth import JWKSCache

        cache = JWKSCache()
        mock_keys = {"keys": [{"kid": "test-key", "kty": "RSA"}]}

        # Manually set cache as if recently fetched
        cache._keys = mock_keys
        cache._fetched_at = time.time()

        with patch.object(cache, "_fetch_keys", new_callable=AsyncMock) as mock_fetch:
            result = await cache.get_keys()

            mock_fetch.assert_not_called()
            assert result == mock_keys

    @pytest.mark.asyncio
    async def test_cache_at_55_min_triggers_background_refresh(self):
        """Cache at 55 min returns immediately and spawns background refresh."""
        from app.core.auth import JWKSCache

        cache = JWKSCache()
        mock_keys = {"keys": [{"kid": "test-key", "kty": "RSA"}]}
        new_keys = {"keys": [{"kid": "new-key", "kty": "RSA"}]}

        # Set cache as fetched 56 minutes ago (within refresh window)
        cache._keys = mock_keys
        cache._fetched_at = time.time() - (56 * 60)

        with patch.object(
            cache, "_fetch_keys", new_callable=AsyncMock, return_value=new_keys
        ) as mock_fetch:
            # Should return old keys immediately
            result = await cache.get_keys()
            assert result == mock_keys

            # Wait for background task to complete
            await asyncio.sleep(0.1)

            # Background fetch should have been called
            mock_fetch.assert_called_once()

            # Cache should now have new keys
            assert cache._keys == new_keys

    @pytest.mark.asyncio
    async def test_expired_cache_falls_back_to_sync_fetch(self):
        """Expired cache (>1hr) does synchronous fetch."""
        from app.core.auth import JWKSCache

        cache = JWKSCache()
        new_keys = {"keys": [{"kid": "new-key", "kty": "RSA"}]}

        # Set cache as fetched 2 hours ago (expired)
        cache._keys = {"keys": [{"kid": "old-key"}]}
        cache._fetched_at = time.time() - (2 * 60 * 60)

        with patch.object(
            cache, "_fetch_keys", new_callable=AsyncMock, return_value=new_keys
        ) as mock_fetch:
            result = await cache.get_keys()

            # Should have fetched synchronously
            mock_fetch.assert_called_once()
            assert result == new_keys

    @pytest.mark.asyncio
    async def test_concurrent_access_uses_lock(self):
        """Concurrent access uses lock to prevent duplicate fetches."""
        from app.core.auth import JWKSCache

        cache = JWKSCache()
        mock_keys = {"keys": [{"kid": "test-key", "kty": "RSA"}]}

        fetch_count = 0

        async def slow_fetch():
            nonlocal fetch_count
            fetch_count += 1
            await asyncio.sleep(0.1)
            return mock_keys

        with patch.object(cache, "_fetch_keys", new_callable=AsyncMock, side_effect=slow_fetch):
            # Start multiple concurrent requests
            results = await asyncio.gather(
                cache.get_keys(),
                cache.get_keys(),
                cache.get_keys(),
            )

            # All should get same result
            assert all(r == mock_keys for r in results)

            # But fetch should only happen once
            assert fetch_count == 1

    @pytest.mark.asyncio
    async def test_background_fetch_failure_keeps_old_keys(self):
        """Background refresh failure keeps old keys and logs warning."""
        from app.core.auth import JWKSCache

        cache = JWKSCache()
        old_keys = {"keys": [{"kid": "old-key", "kty": "RSA"}]}

        # Set cache at refresh threshold
        cache._keys = old_keys
        cache._fetched_at = time.time() - (56 * 60)

        with patch.object(
            cache, "_fetch_keys", new_callable=AsyncMock, side_effect=Exception("Network error")
        ):
            with patch("app.core.auth.logger") as mock_logger:
                result = await cache.get_keys()

                # Wait for background task
                await asyncio.sleep(0.1)

                # Should return old keys
                assert result == old_keys

                # Should still have old keys (not cleared)
                assert cache._keys == old_keys

                # Should have logged warning
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_invalidate_clears_cache(self):
        """invalidate() clears cache, forcing next fetch."""
        from app.core.auth import JWKSCache

        cache = JWKSCache()
        cache._keys = {"keys": [{"kid": "test-key"}]}
        cache._fetched_at = time.time()

        cache.invalidate()

        assert cache._keys is None
        assert cache._fetched_at is None

    @pytest.mark.asyncio
    async def test_empty_cache_fetches_keys(self):
        """Empty cache triggers fetch on first get_keys call."""
        from app.core.auth import JWKSCache

        cache = JWKSCache()
        mock_keys = {"keys": [{"kid": "test-key", "kty": "RSA"}]}

        # Cache is empty by default
        assert cache._keys is None
        assert cache._fetched_at is None

        with patch.object(
            cache, "_fetch_keys", new_callable=AsyncMock, return_value=mock_keys
        ) as mock_fetch:
            result = await cache.get_keys()

            mock_fetch.assert_called_once()
            assert result == mock_keys
            assert cache._keys == mock_keys
            assert cache._fetched_at is not None

    @pytest.mark.asyncio
    async def test_cache_ttl_constants(self):
        """Cache has correct TTL and refresh constants."""
        from app.core.auth import JWKSCache

        cache = JWKSCache()

        assert cache.TTL == 3600  # 1 hour
        assert cache.REFRESH_BEFORE == 300  # 5 minutes
