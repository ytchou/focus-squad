"""
Celery application configuration for Focus Squad.

Handles background task scheduling for:
- LiveKit room creation (T-30s before session)
- Session cleanup (room deletion after session ends)
- Daily credit refresh (00:05 UTC)
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "focus_squad",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.livekit_tasks",
        "app.tasks.credit_tasks",
        "app.tasks.session_tasks",
        "app.tasks.schedule_tasks",
        "app.tasks.rating_tasks",
        "app.tasks.analytics_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task execution
    task_track_started=True,
    task_time_limit=300,  # 5 minute hard limit
    task_soft_time_limit=240,  # 4 minute soft limit
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    # Worker
    worker_prefetch_multiplier=1,  # Fair task distribution
    worker_concurrency=4,  # Concurrent tasks per worker
    # Beat schedule for periodic tasks
    beat_schedule={
        "refresh-credits-daily": {
            "task": "app.tasks.credit_tasks.refresh_due_credits",
            "schedule": crontab(hour=0, minute=5),  # Daily at 00:05 UTC
        },
        "progress-session-phases": {
            "task": "app.tasks.session_tasks.progress_session_phases",
            "schedule": 30.0,  # Every 30 seconds
        },
        "create-scheduled-sessions-hourly": {
            "task": "app.tasks.schedule_tasks.create_scheduled_sessions",
            "schedule": crontab(minute=0),  # Every hour at :00
        },
        "cleanup-expired-pending-ratings": {
            "task": "app.tasks.rating_tasks.cleanup_expired_pending_ratings",
            "schedule": crontab(hour=1, minute=0),  # Daily at 01:00 UTC
        },
        "cleanup-old-analytics": {
            "task": "app.tasks.analytics_tasks.cleanup_old_analytics",
            "schedule": crontab(hour=2, minute=0),  # Daily at 02:00 UTC
        },
    },
)
