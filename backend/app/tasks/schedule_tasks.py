"""
Celery tasks for recurring schedule management.

Handles automatic creation of private sessions from recurring schedules.
Runs hourly via Celery beat.
"""

import logging

from app.core.celery_app import celery_app
from app.services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.schedule_tasks.create_scheduled_sessions")
def create_scheduled_sessions() -> dict:
    """
    Look ahead and create private sessions for recurring schedules.

    For each active schedule, checks if today's day-of-week matches,
    converts the local slot_time to UTC, and creates a private session
    with invitations for all partners.

    Returns:
        Summary dict with sessions_created and invitations_sent counts
    """
    service = ScheduleService()
    result = service.create_scheduled_sessions()

    logger.info(
        "Schedule task completed: %d sessions created, %d invitations sent",
        result["sessions_created"],
        result["invitations_sent"],
    )

    return result
