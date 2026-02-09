"""Analytics service for tracking session behavior events.

Tracks waiting room behavior for no-show analysis and user engagement metrics.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from supabase import Client

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for tracking analytics events (fire-and-forget, non-blocking)."""

    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def track_event(
        self,
        user_id: UUID,
        session_id: UUID,
        event_type: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Track an analytics event (fire-and-forget, non-blocking).

        Args:
            user_id: ID of the user performing the action
            session_id: ID of the session
            event_type: Type of event (e.g., "waiting_room_entered")
            metadata: Optional metadata (e.g., wait_minutes, is_immediate)

        Event types:
            - waiting_room_entered: User matched and entered waiting room
            - waiting_room_resumed: User resumed waiting room after page reload
            - waiting_room_abandoned: User left early (before session start)
            - session_joined_from_waiting_room: User successfully joined session

        Note:
            Analytics failures should not break user flow. Errors are logged
            but not raised.
        """
        try:
            # Insert event into analytics table
            self.supabase.table("session_analytics_events").insert(
                {
                    "user_id": str(user_id),
                    "session_id": str(session_id),
                    "event_type": event_type,
                    "metadata": metadata or {},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ).execute()
        except Exception as e:
            logger.warning("Failed to track event '%s': %s", event_type, e)
