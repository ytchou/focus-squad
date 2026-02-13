"""
Celery tasks for rating system management.

Handles:
- Cleanup of expired pending_ratings records (daily)
"""

import logging
from datetime import datetime, timezone

from app.core.celery_app import celery_app
from app.core.database import get_supabase

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def cleanup_expired_pending_ratings(self) -> dict:
    """
    Delete expired uncompleted pending_ratings records.

    This task runs daily at 01:00 UTC via Celery beat.
    It removes pending_ratings where:
    - completed_at IS NULL (not yet submitted or skipped)
    - expires_at < now (past the 48-hour deadline)

    This prevents stale records from blocking users indefinitely
    and keeps the pending_ratings table clean.

    Returns:
        Dict with count of deleted records
    """
    logger.info("Starting pending_ratings cleanup task")

    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    try:
        # Delete expired, uncompleted pending_ratings
        result = (
            supabase.table("pending_ratings")
            .delete()
            .is_("completed_at", "null")
            .lt("expires_at", now)
            .execute()
        )

        deleted_count = len(result.data or [])
        logger.info(f"Cleaned up {deleted_count} expired pending_ratings")

        return {"deleted_count": deleted_count}

    except Exception as e:
        logger.error(f"Failed to cleanup expired pending_ratings: {e}")
        # Retry on failure
        raise self.retry(exc=e)
