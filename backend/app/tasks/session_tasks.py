"""
Celery tasks for session phase management.

Handles:
- Periodic phase progression for active sessions
"""

import logging
from datetime import datetime, timezone

from app.core.celery_app import celery_app
from app.core.database import get_supabase
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)


BATCH_SIZE = 50


@celery_app.task
def progress_session_phases() -> dict:
    """
    Progress active sessions to their correct phase based on elapsed time.

    Runs every 30 seconds via Celery beat. For each non-ended session:
    1. Calculate expected phase from elapsed time
    2. Update current_phase and phase_started_at if changed
    3. If session should be ended, mark it and schedule cleanup

    Processes sessions in batches of BATCH_SIZE to avoid unbounded memory usage.

    Returns:
        Dict with total sessions checked across all batches and count progressed
    """
    supabase = get_supabase()
    session_service = SessionService(supabase=supabase)

    now = datetime.now(timezone.utc)
    total_checked = 0
    progressed = 0
    offset = 0

    while True:
        result = (
            supabase.table("sessions")
            .select("id, start_time, current_phase")
            .neq("current_phase", "ended")
            .order("id")
            .range(offset, offset + BATCH_SIZE - 1)
            .execute()
        )

        sessions = result.data or []
        if not sessions:
            break

        total_checked += len(sessions)

        for session in sessions:
            current_phase = session["current_phase"]
            expected_phase = session_service.calculate_current_phase(session)

            if expected_phase.value != current_phase:
                supabase.table("sessions").update(
                    {
                        "current_phase": expected_phase.value,
                        "phase_started_at": now.isoformat(),
                    }
                ).eq("id", session["id"]).execute()

                progressed += 1
                logger.info(f"Session {session['id']}: {current_phase} -> {expected_phase.value}")

                # If transitioning to ended, schedule cleanup
                if expected_phase.value == "ended":
                    try:
                        from app.tasks.livekit_tasks import cleanup_ended_session

                        cleanup_ended_session.apply_async(
                            args=[session["id"]],
                            countdown=60,
                        )
                        logger.info(f"Scheduled cleanup for ended session {session['id']}")
                    except Exception as e:
                        logger.warning(f"Failed to schedule cleanup: {e}")

        if len(sessions) < BATCH_SIZE:
            break

        offset += BATCH_SIZE

    return {"checked": total_checked, "progressed": progressed}
