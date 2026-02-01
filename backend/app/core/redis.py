from typing import Optional

from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings

settings = get_settings()

_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection pool."""
    global _redis_pool, _redis_client
    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=10,
            decode_responses=True,
        )
        _redis_client = Redis(connection_pool=_redis_pool)


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
