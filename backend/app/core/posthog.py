"""PostHog analytics client for server-side event tracking.

Fire-and-forget pattern: analytics failures never break business logic.
Uses user_id (internal DB UUID) as distinct_id for person linking.
"""

import logging
from typing import Optional

import posthog as _posthog

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_initialized = False


def init_posthog() -> None:
    """Initialize PostHog client. Call once at app startup."""
    global _initialized
    settings = get_settings()

    if not settings.posthog_enabled or not settings.posthog_api_key:
        logger.info("PostHog disabled (no API key or posthog_enabled=False)")
        return

    _posthog.api_key = settings.posthog_api_key
    _posthog.host = settings.posthog_host
    _posthog.debug = settings.debug
    _initialized = True
    logger.info("PostHog initialized (host=%s)", settings.posthog_host)


def shutdown_posthog() -> None:
    """Flush pending events and shut down. Call at app shutdown."""
    if _initialized:
        _posthog.flush()
        _posthog.shutdown()
        logger.info("PostHog shut down")


def capture(
    user_id: str,
    event: str,
    properties: Optional[dict] = None,
    session_id: Optional[str] = None,
) -> None:
    """Track an event in PostHog (fire-and-forget).

    Args:
        user_id: Internal DB user ID (UUID string) used as distinct_id.
        event: Event name in noun_verb format (e.g., "session_match_succeeded").
        properties: Event properties dict.
        session_id: If provided, attaches session Group for per-table analytics.
    """
    if not _initialized:
        return

    try:
        props = dict(properties) if properties else {}

        groups = {}
        if session_id:
            groups["session"] = session_id
            props["session_id"] = session_id

        _posthog.capture(
            distinct_id=user_id,
            event=event,
            properties=props,
            groups=groups if groups else None,
        )
    except Exception as e:
        logger.warning("PostHog capture failed for '%s': %s", event, e)


def set_person_properties(user_id: str, properties: dict) -> None:
    """Update person properties in PostHog (e.g., after tier change)."""
    if not _initialized:
        return

    try:
        _posthog.capture(
            distinct_id=user_id,
            event="$set",
            properties={"$set": properties},
        )
    except Exception as e:
        logger.warning("PostHog $set failed: %s", e)
