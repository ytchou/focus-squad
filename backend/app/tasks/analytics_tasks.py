"""
Analytics cleanup tasks.

Handles:
- Deleting analytics events older than retention period (1 year)
"""

import logging

from celery import shared_task

from app.core.database import get_supabase

logger = logging.getLogger(__name__)

RETENTION_INTERVAL = "1 year"
BATCH_SIZE = 1000


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def cleanup_old_analytics(self):
    """
    Delete analytics events older than 1 year.

    Uses batch deletion (1000 rows at a time) to avoid lock contention.
    Runs daily at 02:00 UTC via Celery Beat.
    """
    supabase = get_supabase()
    total_deleted = 0

    while True:
        try:
            result = supabase.rpc(
                "delete_old_analytics",
                {"cutoff_interval": RETENTION_INTERVAL, "batch_limit": BATCH_SIZE}
            ).execute()

            deleted_count = result.data.get("deleted", 0) if result.data else 0
            total_deleted += deleted_count

            logger.debug(f"Analytics cleanup batch: deleted {deleted_count} events")

            if deleted_count < BATCH_SIZE:
                break  # No more rows to delete

        except Exception as exc:
            logger.error(f"Analytics cleanup failed after deleting {total_deleted}: {exc}")
            raise self.retry(exc=exc)

    logger.info(f"Analytics cleanup complete: deleted {total_deleted} events older than {RETENTION_INTERVAL}")
    return {"deleted": total_deleted}
