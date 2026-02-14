"""
App-level Redis cache utility for synchronous services.

Provides cache_get / cache_set / cache_delete / cache_delete_pattern.
All operations are wrapped in try/except — cache failures never break the app.
Uses a separate sync Redis connection (services are synchronous).
"""

import json
import logging
from typing import Any, Optional

from redis import Redis as SyncRedis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_sync_redis: Optional[SyncRedis] = None


def _get_cache_client() -> SyncRedis:
    """Lazy-init sync Redis client for caching."""
    global _sync_redis
    if _sync_redis is None:
        settings = get_settings()
        _sync_redis = SyncRedis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _sync_redis


def cache_get(key: str) -> Optional[Any]:
    """Get a JSON-deserialized value from cache. Returns None on miss or error."""
    try:
        raw = _get_cache_client().get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.warning("Cache get failed for key=%s", key, exc_info=True)
        return None


def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    """Set a JSON-serialized value in cache with TTL in seconds."""
    try:
        _get_cache_client().set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        logger.warning("Cache set failed for key=%s", key, exc_info=True)


def cache_delete(key: str) -> None:
    """Delete a single cache key."""
    try:
        _get_cache_client().delete(key)
    except Exception:
        logger.warning("Cache delete failed for key=%s", key, exc_info=True)


def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a glob pattern using SCAN (non-blocking)."""
    try:
        client = _get_cache_client()
        cursor = 0
        while True:
            cursor, keys = client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                client.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.warning("Cache delete pattern failed for pattern=%s", pattern, exc_info=True)


def reset_cache_client() -> None:
    """Reset sync Redis client (for testing)."""
    global _sync_redis
    _sync_redis = None
