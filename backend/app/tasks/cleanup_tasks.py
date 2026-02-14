import logging

from app.core.celery_app import celery_app
from app.core.database import get_supabase

logger = logging.getLogger(__name__)


@celery_app.task(name="cleanup.delete_old_chat_messages")
def delete_old_chat_messages():
    """Daily task to delete chat messages older than 90 days."""
    try:
        supabase = get_supabase()
        result = supabase.rpc("delete_old_chat_messages", {"retention_days": 90}).execute()
        deleted = result.data if result.data is not None else 0
        logger.info("Chat message cleanup: deleted %s old messages", deleted)
        return deleted
    except Exception:
        logger.exception("Chat message cleanup failed")
        raise
