"""
Celery tasks for credit system management.

Handles:
- Daily credit refresh for users whose 7-day cycle has expired
"""

import logging
from datetime import datetime, timedelta, timezone

from app.core.celery_app import celery_app
from app.core.database import get_supabase
from app.services.credit_service import CreditService

logger = logging.getLogger(__name__)


BATCH_SIZE = 100


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def refresh_due_credits(self) -> dict:
    """
    Refresh credits for all users whose 7-day cycle has expired.

    This task runs daily at 00:05 UTC via Celery beat.
    It finds all users whose credit_cycle_start + 7 days <= today
    and refreshes their credits.

    Processes users in batches of BATCH_SIZE to avoid unbounded memory usage.

    Returns:
        Dict with count of users refreshed
    """
    logger.info("Starting daily credit refresh task")

    supabase = get_supabase()
    credit_service = CreditService(supabase=supabase)

    # Find users due for refresh
    # credit_cycle_start + 7 days <= today means they're due
    cutoff_date = (datetime.now(timezone.utc).date() - timedelta(days=7)).isoformat()

    refreshed = 0
    errors = 0
    offset = 0

    while True:
        result = (
            supabase.table("credits")
            .select("user_id, credit_cycle_start")
            .lte("credit_cycle_start", cutoff_date)
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )

        users_to_refresh = result.data or []
        if not users_to_refresh:
            break

        logger.info(f"Processing batch of {len(users_to_refresh)} users (offset {offset})")

        for user_record in users_to_refresh:
            user_id = user_record["user_id"]
            try:
                transaction = credit_service.refresh_credits_for_user(user_id)
                if transaction:
                    refreshed += 1
                    logger.debug(f"Refreshed credits for user {user_id}")
            except Exception as e:
                errors += 1
                logger.error(f"Failed to refresh credits for user {user_id}: {e}")

        if len(users_to_refresh) < BATCH_SIZE:
            break

        offset += BATCH_SIZE

    logger.info(f"Credit refresh complete. Refreshed: {refreshed}, Errors: {errors}")

    return {"refreshed_count": refreshed, "errors": errors}


@celery_app.task
def refresh_single_user_credits(user_id: str) -> dict:
    """
    Refresh credits for a single user (manual trigger or on-demand).

    Args:
        user_id: User UUID to refresh

    Returns:
        Dict with success status and new balance
    """
    logger.info(f"Refreshing credits for user {user_id}")

    credit_service = CreditService()

    try:
        transaction = credit_service.refresh_credits_for_user(user_id)
        if transaction:
            return {
                "success": True,
                "refreshed": True,
                "amount_added": transaction.amount,
            }
        else:
            return {
                "success": True,
                "refreshed": False,
                "message": "User not due for refresh yet",
            }
    except Exception as e:
        logger.error(f"Failed to refresh credits for user {user_id}: {e}")
        return {"success": False, "error": str(e)}
