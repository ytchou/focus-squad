# Phase 5 P0: Production Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden Focus Squad backend for production by validating secrets at startup, implementing JWKS cache TTL, testing Redis connections, and validating rating session IDs.

**Architecture:** Four independent hardening tasks. Each adds validation/resilience to existing code without changing business logic. TDD approach: write failing tests first, then implement minimal code to pass.

**Tech Stack:** Python 3.9+, Pydantic v2, FastAPI, asyncio, Redis, Vitest (frontend)

**Design Doc:** `docs/plans/2026-02-13-p0-production-hardening-design.md`

---

## Task 1: Startup Secret Validation

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/tests/unit/core/test_config.py`

### Step 1.1: Write failing tests for secret validation

```python
# backend/tests/unit/core/test_config.py
"""Tests for config secret validation."""

import pytest
from unittest.mock import patch


class TestSecretValidation:
    """Test that required secrets are validated at startup."""

    def test_missing_single_secret_raises_error(self):
        """Missing one required secret raises ValueError."""
        env = {
            "SUPABASE_URL": "",  # Missing
            "SUPABASE_ANON_KEY": "test-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "LIVEKIT_API_KEY": "test-livekit-key",
            "LIVEKIT_API_SECRET": "test-livekit-secret",
            "LIVEKIT_URL": "wss://test.livekit.cloud",
        }
        with patch.dict("os.environ", env, clear=True):
            from pydantic import ValidationError
            from app.core.config import Settings

            with pytest.raises(ValidationError) as exc_info:
                Settings()

            assert "SUPABASE_URL" in str(exc_info.value)

    def test_missing_multiple_secrets_lists_all(self):
        """Missing multiple secrets lists all in error message."""
        env = {
            "SUPABASE_URL": "",  # Missing
            "SUPABASE_ANON_KEY": "",  # Missing
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "LIVEKIT_API_KEY": "",  # Missing
            "LIVEKIT_API_SECRET": "test-livekit-secret",
            "LIVEKIT_URL": "wss://test.livekit.cloud",
        }
        with patch.dict("os.environ", env, clear=True):
            from pydantic import ValidationError
            from app.core.config import Settings

            with pytest.raises(ValidationError) as exc_info:
                Settings()

            error_str = str(exc_info.value)
            assert "SUPABASE_URL" in error_str
            assert "SUPABASE_ANON_KEY" in error_str
            assert "LIVEKIT_API_KEY" in error_str

    def test_all_secrets_present_succeeds(self):
        """All required secrets present allows Settings to load."""
        env = {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "LIVEKIT_API_KEY": "test-livekit-key",
            "LIVEKIT_API_SECRET": "test-livekit-secret",
            "LIVEKIT_URL": "wss://test.livekit.cloud",
        }
        with patch.dict("os.environ", env, clear=True):
            from app.core.config import Settings

            settings = Settings()
            assert settings.supabase_url == "https://test.supabase.co"

    def test_jwt_secret_is_optional(self):
        """jwt_secret is optional (not required for Supabase JWKS auth)."""
        env = {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "LIVEKIT_API_KEY": "test-livekit-key",
            "LIVEKIT_API_SECRET": "test-livekit-secret",
            "LIVEKIT_URL": "wss://test.livekit.cloud",
            # JWT_SECRET intentionally not set
        }
        with patch.dict("os.environ", env, clear=True):
            from app.core.config import Settings

            settings = Settings()
            assert settings.jwt_secret == ""  # Default empty is OK
```

### Step 1.2: Run tests to verify they fail

Run: `cd backend && python -m pytest tests/unit/core/test_config.py -v`

Expected: FAIL — no validation exists yet

### Step 1.3: Implement secret validation in config.py

```python
# backend/app/core/config.py
from functools import lru_cache
from typing import ClassVar

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Required secrets (validated at startup)
    REQUIRED_SECRETS: ClassVar[list[str]] = [
        "supabase_url",
        "supabase_anon_key",
        "supabase_service_role_key",
        "livekit_api_key",
        "livekit_api_secret",
        "livekit_url",
    ]

    # App
    app_name: str = "Focus Squad API"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"

    # LiveKit
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_url: str = ""

    # JWT (optional - not used with Supabase JWKS auth)
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"

    # Rate limiting
    rate_limit_enabled: bool = True

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        """Validate that all required secrets are set (non-empty)."""
        missing = []
        for secret_name in self.REQUIRED_SECRETS:
            value = getattr(self, secret_name, "")
            if not value or not value.strip():
                # Convert to uppercase env var name for error message
                env_name = secret_name.upper()
                missing.append(env_name)

        if missing:
            raise ValueError(
                f"Missing required secrets: {', '.join(missing)}. "
                "Set these environment variables before starting the application."
            )

        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

### Step 1.4: Run tests to verify they pass

Run: `cd backend && python -m pytest tests/unit/core/test_config.py -v`

Expected: 4 tests PASS

### Step 1.5: Run full backend test suite

Run: `cd backend && python -m pytest --tb=short`

Expected: All existing tests pass (may need to update test fixtures that create Settings)

### Step 1.6: Commit

```bash
git add backend/app/core/config.py backend/tests/unit/core/test_config.py
git commit -m "feat(config): add startup secret validation

Validate required secrets at app startup. Missing secrets now cause
immediate failure with clear error message listing all missing vars.

Required: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY,
LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL

JWT_SECRET remains optional (unused with Supabase JWKS auth).

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Redis Connection Validation with Retry

**Files:**
- Modify: `backend/app/core/redis.py`
- Create: `backend/tests/unit/core/test_redis.py`

### Step 2.1: Write failing tests for Redis retry

```python
# backend/tests/unit/core/test_redis.py
"""Tests for Redis connection validation with retry."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError


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
        mock_redis.ping = AsyncMock(
            side_effect=[RedisConnectionError("Connection refused"), True]
        )

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
        mock_redis.ping = AsyncMock(
            side_effect=RedisConnectionError("Connection refused")
        )

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
        mock_redis.ping = AsyncMock(
            side_effect=RedisConnectionError("Connection refused")
        )

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
```

### Step 2.2: Run tests to verify they fail

Run: `cd backend && python -m pytest tests/unit/core/test_redis.py -v`

Expected: FAIL — no retry logic exists

### Step 2.3: Implement Redis retry logic

```python
# backend/app/core/redis.py
import asyncio
import logging
from typing import Optional

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import RedisError

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]  # Exponential backoff in seconds


def _reset_redis() -> None:
    """Reset Redis state (for testing)."""
    global _redis_pool, _redis_client
    _redis_pool = None
    _redis_client = None


async def init_redis() -> None:
    """Initialize Redis connection pool with connectivity check.

    Retries connection up to 3 times with exponential backoff (1s, 2s, 4s).
    Raises RuntimeError if all attempts fail.
    """
    global _redis_pool, _redis_client

    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=10,
            decode_responses=True,
        )
        _redis_client = Redis(connection_pool=_redis_pool)

    # Verify connectivity with retry
    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES):
        try:
            await _redis_client.ping()
            logger.info("Redis connection verified")
            return
        except RedisError as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(
                    "Redis ping failed (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1,
                    MAX_RETRIES,
                    delay,
                    e,
                )
                await asyncio.sleep(delay)

    raise RuntimeError(
        f"Redis connection failed after {MAX_RETRIES} attempts: {last_error}"
    )


async def close_redis() -> None:
    """Close Redis connection pool."""
    global _redis_pool, _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None


def get_redis() -> Redis:
    """Get Redis client instance.

    Must call init_redis() during application startup before using this.

    Returns:
        Redis client instance

    Raises:
        RuntimeError: If Redis is not initialized
    """
    if _redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_client


class SessionStateKeys:
    """Redis key patterns for session state management."""

    @staticmethod
    def session(session_id: str) -> str:
        """Key for session metadata."""
        return f"session:{session_id}"

    @staticmethod
    def session_participants(session_id: str) -> str:
        """Key for session participant set."""
        return f"session:{session_id}:participants"

    @staticmethod
    def session_phase(session_id: str) -> str:
        """Key for current session phase."""
        return f"session:{session_id}:phase"

    @staticmethod
    def user_active_session(user_id: str) -> str:
        """Key for user's current active session."""
        return f"user:{user_id}:active_session"

    @staticmethod
    def matching_queue(table_mode: str = "forced_audio") -> str:
        """Key for quick match queue by table mode."""
        return f"matching:queue:{table_mode}"
```

### Step 2.4: Run tests to verify they pass

Run: `cd backend && python -m pytest tests/unit/core/test_redis.py -v`

Expected: 4 tests PASS

### Step 2.5: Run full backend test suite

Run: `cd backend && python -m pytest --tb=short`

Expected: All tests pass

### Step 2.6: Commit

```bash
git add backend/app/core/redis.py backend/tests/unit/core/test_redis.py
git commit -m "feat(redis): add connection validation with retry

Ping Redis during init_redis() to verify connectivity.
Retry up to 3 times with exponential backoff (1s, 2s, 4s).
Fail fast with RuntimeError if Redis unreachable.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Rating SessionId Validation (Frontend)

**Files:**
- Modify: `frontend/src/stores/rating-store.ts`
- Create: `frontend/src/stores/__tests__/rating-store.test.ts`

### Step 3.1: Write failing tests for sessionId validation

```typescript
// frontend/src/stores/__tests__/rating-store.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useRatingStore } from "../rating-store";

// Mock the API client
vi.mock("@/lib/api/client", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

describe("rating-store sessionId validation", () => {
  beforeEach(() => {
    // Reset store state
    useRatingStore.getState().reset();
  });

  describe("submitRatings", () => {
    it("proceeds when sessionId matches pendingSessionId", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post).mockResolvedValueOnce({});

      const store = useRatingStore.getState();

      // Set up pending ratings for session-123
      store.setPendingRatings("session-123", [
        {
          user_id: "user-1",
          username: "alice",
          display_name: "Alice",
          avatar_config: {},
        },
      ]);

      // Set a rating
      store.setRating("user-1", "green");

      // Submit with matching sessionId
      await store.submitRatings("session-123");

      expect(mockPost).toHaveBeenCalledWith(
        "/api/v1/sessions/session-123/rate",
        expect.any(Object)
      );
      expect(useRatingStore.getState().error).toBeNull();
    });

    it("sets error when sessionId does not match pendingSessionId", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post);
      mockPost.mockClear();

      const store = useRatingStore.getState();

      // Set up pending ratings for session-123
      store.setPendingRatings("session-123", [
        {
          user_id: "user-1",
          username: "alice",
          display_name: "Alice",
          avatar_config: {},
        },
      ]);

      // Try to submit for different session
      await store.submitRatings("session-456");

      // Should NOT call API
      expect(mockPost).not.toHaveBeenCalled();

      // Should set error
      expect(useRatingStore.getState().error).toBe(
        "Session mismatch: cannot rate a different session"
      );
    });

    it("proceeds when no pendingSessionId is set (edge case)", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post).mockResolvedValueOnce({});

      const store = useRatingStore.getState();

      // No pending ratings set, but try to submit anyway
      // This is an edge case - should proceed and let backend validate
      await store.submitRatings("session-123");

      expect(mockPost).toHaveBeenCalled();
    });
  });

  describe("skipAll", () => {
    it("sets error when sessionId does not match pendingSessionId", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post);
      mockPost.mockClear();

      const store = useRatingStore.getState();

      // Set up pending ratings for session-123
      store.setPendingRatings("session-123", [
        {
          user_id: "user-1",
          username: "alice",
          display_name: "Alice",
          avatar_config: {},
        },
      ]);

      // Try to skip for different session
      await store.skipAll("session-456");

      // Should NOT call API
      expect(mockPost).not.toHaveBeenCalled();

      // Should set error
      expect(useRatingStore.getState().error).toBe(
        "Session mismatch: cannot rate a different session"
      );
    });
  });
});
```

### Step 3.2: Run tests to verify they fail

Run: `cd frontend && npm run test -- src/stores/__tests__/rating-store.test.ts`

Expected: Tests for session mismatch FAIL (no validation exists)

### Step 3.3: Implement sessionId validation in rating-store

Update `submitRatings` and `skipAll` in `frontend/src/stores/rating-store.ts`:

```typescript
// In the store definition, update submitRatings:
submitRatings: async (sessionId) => {
  const { ratings, pendingSessionId } = get();

  // Guard: prevent rating wrong session
  if (pendingSessionId && sessionId !== pendingSessionId) {
    set({ error: "Session mismatch: cannot rate a different session" });
    return;
  }

  set({ isSubmitting: true, error: null });

  try {
    const ratingsPayload = Object.entries(ratings)
      .filter(([, entry]) => entry.value !== null)
      .map(([rateeId, entry]) => ({
        ratee_id: rateeId,
        rating: entry.value as "green" | "red" | "skip",
        ...(entry.value === "red" && entry.reasons.length > 0 ? { reasons: entry.reasons } : {}),
        ...(entry.value === "red" &&
        entry.reasons.includes("other") &&
        entry.otherReasonText.trim()
          ? { other_reason_text: entry.otherReasonText.trim() }
          : {}),
      }));

    await api.post(`/api/v1/sessions/${sessionId}/rate`, {
      ratings: ratingsPayload,
    });

    set({
      ...initialState,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to submit ratings";
    set({ error: message, isSubmitting: false });
  }
},

// Update skipAll:
skipAll: async (sessionId) => {
  const { pendingSessionId } = get();

  // Guard: prevent skipping wrong session
  if (pendingSessionId && sessionId !== pendingSessionId) {
    set({ error: "Session mismatch: cannot rate a different session" });
    return;
  }

  set({ isSubmitting: true, error: null });

  try {
    await api.post(`/api/v1/sessions/${sessionId}/rate/skip`);

    set({
      ...initialState,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to skip ratings";
    set({ error: message, isSubmitting: false });
  }
},
```

### Step 3.4: Run tests to verify they pass

Run: `cd frontend && npm run test -- src/stores/__tests__/rating-store.test.ts`

Expected: All 4 tests PASS

### Step 3.5: Run full frontend test suite

Run: `cd frontend && npm run test`

Expected: All tests pass

### Step 3.6: Commit

```bash
git add frontend/src/stores/rating-store.ts frontend/src/stores/__tests__/rating-store.test.ts
git commit -m "feat(rating-store): add sessionId validation guard

Prevent submitting ratings for wrong session by validating sessionId
matches pendingSessionId before API call. Provides immediate UX
feedback instead of confusing backend error.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: JWKS Cache with Background Refresh

**Files:**
- Modify: `backend/app/core/auth.py`
- Modify: `backend/app/core/middleware.py` (make token validation async)
- Create: `backend/tests/unit/core/test_jwks_cache.py`

### Step 4.1: Write failing tests for JWKS cache

```python
# backend/tests/unit/core/test_jwks_cache.py
"""Tests for JWKS cache with TTL and background refresh."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

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
```

### Step 4.2: Run tests to verify they fail

Run: `cd backend && python -m pytest tests/unit/core/test_jwks_cache.py -v`

Expected: FAIL — JWKSCache class doesn't exist

### Step 4.3: Implement JWKSCache class

```python
# backend/app/core/auth.py
"""
Authentication module for Supabase JWT validation.

Provides FastAPI dependencies for extracting and validating
JWT tokens from Supabase Auth using JWKS (asymmetric keys).

Two modes of operation:
1. Standalone: Dependencies validate tokens directly (legacy)
2. With middleware: Dependencies read from request.state (recommended)
"""

import asyncio
import logging
import time
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# HTTP Bearer token extraction
security = HTTPBearer(auto_error=False)


class AuthUser(BaseModel):
    """Authenticated user context from JWT token."""

    auth_id: str  # Supabase auth.uid()
    email: str
    # Add more claims as needed


class AuthOptionalUser(BaseModel):
    """Optional authenticated user (for endpoints that work with or without auth)."""

    auth_id: Optional[str] = None
    email: Optional[str] = None
    is_authenticated: bool = False


class JWKSCache:
    """JWKS cache with TTL and background refresh.

    - Caches JWKS keys for 1 hour
    - Triggers background refresh 5 minutes before expiry
    - Uses asyncio.Lock to prevent concurrent fetches
    - Keeps old keys on background refresh failure
    """

    TTL = 3600  # 1 hour in seconds
    REFRESH_BEFORE = 300  # 5 minutes before expiry

    def __init__(self) -> None:
        self._keys: Optional[dict] = None
        self._fetched_at: Optional[float] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def get_keys(self) -> dict:
        """Get JWKS keys, fetching if needed.

        Returns cached keys immediately if valid.
        Triggers background refresh if cache is expiring soon.
        Does synchronous fetch if cache is fully expired.
        """
        now = time.time()

        # Check if cache is valid
        if self._keys is not None and self._fetched_at is not None:
            age = now - self._fetched_at

            # Fresh cache - return immediately
            if age < (self.TTL - self.REFRESH_BEFORE):
                return self._keys

            # Cache expiring soon - return old keys and refresh in background
            if age < self.TTL:
                self._schedule_background_refresh()
                return self._keys

        # Cache expired or empty - fetch synchronously
        async with self._lock:
            # Double-check after acquiring lock
            if self._keys is not None and self._fetched_at is not None:
                age = now - self._fetched_at
                if age < self.TTL:
                    return self._keys

            # Fetch new keys
            self._keys = await self._fetch_keys()
            self._fetched_at = time.time()
            return self._keys

    async def _fetch_keys(self) -> dict:
        """Fetch JWKS from Supabase endpoint."""
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=10.0)
            response.raise_for_status()
            return response.json()

    def _schedule_background_refresh(self) -> None:
        """Schedule background refresh if not already running."""
        if self._refresh_task is not None and not self._refresh_task.done():
            return  # Already refreshing

        self._refresh_task = asyncio.create_task(self._background_refresh())

    async def _background_refresh(self) -> None:
        """Refresh cache in background."""
        try:
            async with self._lock:
                new_keys = await self._fetch_keys()
                self._keys = new_keys
                self._fetched_at = time.time()
                logger.info("JWKS cache refreshed in background")
        except Exception as e:
            logger.warning("Background JWKS refresh failed, keeping old keys: %s", e)

    def invalidate(self) -> None:
        """Clear cache, forcing next access to fetch."""
        self._keys = None
        self._fetched_at = None


# Global cache instance
_jwks_cache = JWKSCache()


async def get_jwks() -> dict:
    """
    Fetch JWKS (JSON Web Key Set) from Supabase's well-known endpoint.
    Keys are cached with TTL and background refresh.
    """
    try:
        return await _jwks_cache.get_keys()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch JWKS: {str(e)}",
        )


async def get_signing_key(token: str) -> dict:
    """
    Get the signing key from JWKS that matches the token's key ID (kid).
    """
    jwks = await get_jwks()

    # Get the key ID from the token header
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    kid = unverified_header.get("kid")

    # Find matching key in JWKS
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    # If no kid match, try the first key (some Supabase projects may not use kid)
    if jwks.get("keys"):
        return jwks["keys"][0]

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No matching signing key found",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def decode_supabase_token(token: str) -> dict:
    """
    Decode and validate a Supabase JWT token using JWKS.

    Supabase JWTs contain:
    - sub: user's auth_id (UUID)
    - email: user's email
    - aud: "authenticated" for logged-in users
    - role: "authenticated" or "anon"
    """
    try:
        signing_key = await get_signing_key(token)

        # Decode using the public key from JWKS
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],  # Supabase uses RS256 or ES256
            audience="authenticated",
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthUser:
    """
    FastAPI dependency to get the current authenticated user.

    Usage:
        @router.get("/protected")
        async def protected_route(user: AuthUser = Depends(get_current_user)):
            return {"user_id": user.auth_id}
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = await decode_supabase_token(credentials.credentials)

    # Extract user info from JWT claims
    auth_id = payload.get("sub")
    email = payload.get("email")

    if not auth_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthUser(auth_id=auth_id, email=email or "")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthOptionalUser:
    """
    FastAPI dependency to get an optional authenticated user.

    Returns an unauthenticated user object if no valid token is provided,
    allowing endpoints to work for both authenticated and anonymous users.

    Usage:
        @router.get("/public-or-private")
        async def flexible_route(user: AuthOptionalUser = Depends(get_optional_user)):
            if user.is_authenticated:
                return {"message": f"Hello, {user.email}"}
            return {"message": "Hello, anonymous user"}
    """
    if credentials is None:
        return AuthOptionalUser(is_authenticated=False)

    try:
        payload = await decode_supabase_token(credentials.credentials)
        auth_id = payload.get("sub")
        email = payload.get("email")

        if auth_id:
            return AuthOptionalUser(auth_id=auth_id, email=email, is_authenticated=True)
    except HTTPException:
        pass

    return AuthOptionalUser(is_authenticated=False)


async def get_user_from_state(request: Request) -> AuthOptionalUser:
    """
    Get user from request.state (populated by JWTValidationMiddleware).

    This is more efficient than get_current_user/get_optional_user as
    it avoids re-validating the token when middleware has already done so.

    Usage:
        @router.get("/example")
        async def example(user: AuthOptionalUser = Depends(get_user_from_state)):
            if user.is_authenticated:
                return {"user_id": user.auth_id}
            return {"message": "anonymous"}
    """
    user = getattr(request.state, "user", None)
    if user is not None:
        return user
    return AuthOptionalUser(is_authenticated=False)


async def require_auth_from_state(request: Request) -> AuthUser:
    """
    Require authenticated user from request.state (populated by middleware).

    Raises 401 if user is not authenticated.

    Usage:
        @router.get("/protected")
        async def protected(user: AuthUser = Depends(require_auth_from_state)):
            return {"user_id": user.auth_id}
    """
    user = getattr(request.state, "user", None)

    if user is None or not user.is_authenticated:
        # Check if there was a token error for better error messages
        token_error = getattr(request.state, "token_error", None)
        detail = "Authentication required"
        if token_error:
            detail = f"Authentication failed: {token_error}"

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthUser(auth_id=user.auth_id, email=user.email or "")
```

### Step 4.4: Update middleware to use async token validation

Check and update `backend/app/core/middleware.py` to call async `decode_supabase_token`:

```python
# In middleware.py, update the token validation to use await
# The middleware dispatch method is already async, so just add await
# to the decode_supabase_token call

# Find the line that calls decode_supabase_token and add await:
# Before: payload = decode_supabase_token(token)
# After:  payload = await decode_supabase_token(token)
```

### Step 4.5: Run tests to verify they pass

Run: `cd backend && python -m pytest tests/unit/core/test_jwks_cache.py -v`

Expected: 6 tests PASS

### Step 4.6: Run full backend test suite

Run: `cd backend && python -m pytest --tb=short`

Expected: All tests pass (existing auth tests may need updates for async)

### Step 4.7: Commit

```bash
git add backend/app/core/auth.py backend/app/core/middleware.py backend/tests/unit/core/test_jwks_cache.py
git commit -m "feat(auth): add JWKS cache with TTL and background refresh

Replace global _jwks_cache dict with JWKSCache class:
- 1-hour TTL with 5-minute refresh window
- Background refresh doesn't block requests
- asyncio.Lock prevents concurrent fetches
- Failed background refresh keeps old keys

Convert get_jwks, get_signing_key, decode_supabase_token to async.
Update middleware to use await for token validation.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Update TODO.md and Final Verification

**Files:**
- Modify: `TODO.md`

### Step 5.1: Update TODO.md to mark P0 tasks complete

Mark the following as complete in TODO.md Phase 5 section:
- [x] Add startup secret validation in `config.py`
- [x] Implement JWKS cache TTL (1-hour expiration with background refresh)
- [x] Test Redis connection during init (`await redis.ping()`)
- [x] Validate rating sessionId in rating-store

### Step 5.2: Run full test suites

Backend:
```bash
cd backend && python -m pytest --tb=short
```
Expected: 650+ tests pass

Frontend:
```bash
cd frontend && npm run test
```
Expected: 360+ tests pass

### Step 5.3: Verify app starts with secrets

```bash
cd backend
source venv/bin/activate
# With all secrets in .env
uvicorn main:app --reload
# Should start successfully
```

### Step 5.4: Verify app fails without secrets

```bash
cd backend
# Clear a required secret temporarily
SUPABASE_URL="" uvicorn main:app
# Should fail with clear error message
```

### Step 5.5: Final commit

```bash
git add TODO.md
git commit -m "docs: mark P0 production hardening tasks complete

- Startup secret validation: hard fail with clear error
- JWKS cache: 1-hour TTL with background refresh
- Redis ping: 3 retries with exponential backoff
- Rating sessionId: frontend guard + backend validation

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Verification Checklist

- [ ] Task 1: Secret validation tests pass
- [ ] Task 2: Redis retry tests pass
- [ ] Task 3: Rating sessionId tests pass
- [ ] Task 4: JWKS cache tests pass
- [ ] All backend tests pass (650+)
- [ ] All frontend tests pass (360+)
- [ ] App starts with all secrets
- [ ] App fails clearly without secrets
- [ ] TODO.md updated
