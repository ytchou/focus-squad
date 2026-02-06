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
    include=["app.tasks.livekit_tasks", "app.tasks.credit_tasks"],
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
    },
)
