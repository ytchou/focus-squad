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
