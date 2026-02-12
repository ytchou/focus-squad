"""
Schedule service for recurring accountability partner sessions.

Handles:
- CRUD for recurring schedules (Unlimited plan only)
- Automated session creation from schedules (Celery beat)
- Partner validation and invitation creation

Design doc: output/plan/2026-02-12-accountability-partners-design.md
"""

import logging
from datetime import datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from supabase import Client

from app.core.constants import (
    MAX_RECURRING_SCHEDULES,
    SCHEDULE_LOOKAHEAD_HOURS,
    SESSION_DURATION_MINUTES,
)
from app.core.database import get_supabase
from app.models.schedule import (
    RecurringScheduleCreate,
    RecurringScheduleUpdate,
    ScheduleLimitError,
    ScheduleNotFoundError,
    ScheduleOwnershipError,
    SchedulePermissionError,
)

logger = logging.getLogger(__name__)


class ScheduleService:
    """Service for recurring schedule management."""

    def __init__(self, supabase: Optional[Client] = None) -> None:
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _validate_infinite_tier(self, user_id: str) -> None:
        """Validate that user is on the 'infinite' tier."""
        result = self.supabase.table("credits").select("tier").eq("user_id", user_id).execute()

        if not result.data:
            raise SchedulePermissionError(
                "No credit record found. Recurring schedules require the Unlimited plan."
            )

        tier = result.data[0].get("tier")
        if tier != "infinite":
            raise SchedulePermissionError(
                f"Recurring schedules require the Unlimited plan (current tier: {tier})"
            )

    def _validate_partners(self, creator_id: str, partner_ids: list[str]) -> None:
        """Validate that all partner_ids are accepted partners of the creator."""
        if not partner_ids:
            return

        # Query partnerships where creator is either requester or addressee
        # and the partner is the other party, with status = 'accepted'
        result_as_requester = (
            self.supabase.table("partnerships")
            .select("addressee_id")
            .eq("requester_id", creator_id)
            .eq("status", "accepted")
            .in_("addressee_id", partner_ids)
            .execute()
        )

        result_as_addressee = (
            self.supabase.table("partnerships")
            .select("requester_id")
            .eq("addressee_id", creator_id)
            .eq("status", "accepted")
            .in_("requester_id", partner_ids)
            .execute()
        )

        accepted_partners: set[str] = set()
        for row in result_as_requester.data or []:
            accepted_partners.add(row["addressee_id"])
        for row in result_as_addressee.data or []:
            accepted_partners.add(row["requester_id"])

        missing = set(partner_ids) - accepted_partners
        if missing:
            raise SchedulePermissionError(
                f"Not all partner_ids are accepted partners: {sorted(missing)}"
            )

    def _resolve_partner_names(self, partner_ids: list[str]) -> list[str]:
        """Resolve partner UUIDs to display names."""
        if not partner_ids:
            return []

        result = (
            self.supabase.table("users")
            .select("id, display_name, username")
            .in_("id", partner_ids)
            .execute()
        )

        name_map: dict[str, str] = {}
        for row in result.data or []:
            name_map[row["id"]] = row.get("display_name") or row.get("username") or "Unknown"

        return [name_map.get(pid, "Unknown") for pid in partner_ids]

    def _schedule_to_info(self, schedule: dict) -> dict:
        """Convert a raw schedule DB row to an info dict with partner_names."""
        partner_ids = schedule.get("partner_ids") or []
        partner_names = self._resolve_partner_names(partner_ids)

        slot_time_raw = schedule.get("slot_time", "00:00")
        # Normalize slot_time to HH:MM format (DB may return HH:MM:SS)
        if isinstance(slot_time_raw, str) and slot_time_raw.count(":") == 2:
            slot_time_str = slot_time_raw[:5]
        else:
            slot_time_str = str(slot_time_raw)

        return {
            "id": schedule["id"],
            "label": schedule.get("label"),
            "creator_id": schedule["creator_id"],
            "partner_ids": partner_ids,
            "partner_names": partner_names,
            "days_of_week": schedule.get("days_of_week") or [],
            "slot_time": slot_time_str,
            "timezone": schedule.get("timezone", "Asia/Taipei"),
            "table_mode": schedule.get("table_mode", "forced_audio"),
            "max_seats": schedule.get("max_seats", 4),
            "fill_ai": schedule.get("fill_ai", True),
            "topic": schedule.get("topic"),
            "is_active": schedule.get("is_active", True),
            "created_at": schedule.get("created_at"),
        }

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def create_schedule(self, creator_id: str, data: RecurringScheduleCreate) -> dict:
        """
        Create a recurring schedule.

        Validates:
        - User is on 'infinite' tier
        - All partner_ids are accepted partners
        - User has not exceeded MAX_RECURRING_SCHEDULES

        Args:
            creator_id: UUID of the schedule creator
            data: Schedule creation payload

        Returns:
            Schedule info dict with partner_names populated

        Raises:
            SchedulePermissionError: User not on Unlimited plan or invalid partners
            ScheduleLimitError: Too many existing schedules
        """
        self._validate_infinite_tier(creator_id)
        self._validate_partners(creator_id, data.partner_ids)

        # Check schedule count limit
        count_result = (
            self.supabase.table("recurring_schedules")
            .select("id", count="exact")
            .eq("creator_id", creator_id)
            .execute()
        )
        existing_count = count_result.count or 0
        if existing_count >= MAX_RECURRING_SCHEDULES:
            raise ScheduleLimitError(
                f"Maximum of {MAX_RECURRING_SCHEDULES} recurring schedules reached"
            )

        # Insert the schedule
        insert_data = {
            "creator_id": creator_id,
            "partner_ids": data.partner_ids,
            "days_of_week": data.days_of_week,
            "slot_time": data.slot_time.strftime("%H:%M:%S"),
            "timezone": data.timezone,
            "label": data.label,
            "table_mode": data.table_mode,
            "max_seats": data.max_seats,
            "fill_ai": data.fill_ai,
            "topic": data.topic,
            "is_active": True,
        }

        result = self.supabase.table("recurring_schedules").insert(insert_data).execute()

        if not result.data:
            raise SchedulePermissionError("Failed to create recurring schedule")

        schedule = result.data[0]
        logger.info(
            "Created recurring schedule %s for user %s",
            schedule["id"],
            creator_id,
        )

        return self._schedule_to_info(schedule)

    def list_schedules(self, user_id: str) -> list[dict]:
        """
        List all recurring schedules for a user.

        Args:
            user_id: UUID of the schedule creator

        Returns:
            List of schedule info dicts with partner_names populated
        """
        result = (
            self.supabase.table("recurring_schedules")
            .select("*")
            .eq("creator_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )

        return [self._schedule_to_info(s) for s in (result.data or [])]

    def update_schedule(
        self, schedule_id: str, user_id: str, data: RecurringScheduleUpdate
    ) -> dict:
        """
        Update a recurring schedule.

        Args:
            schedule_id: UUID of the schedule to update
            user_id: UUID of the requesting user
            data: Partial update payload

        Returns:
            Updated schedule info dict

        Raises:
            ScheduleNotFoundError: Schedule does not exist
            ScheduleOwnershipError: User is not the creator
            SchedulePermissionError: Invalid partner_ids
        """
        # Fetch existing schedule
        result = (
            self.supabase.table("recurring_schedules").select("*").eq("id", schedule_id).execute()
        )

        if not result.data:
            raise ScheduleNotFoundError(f"Schedule {schedule_id} not found")

        schedule = result.data[0]

        if schedule["creator_id"] != user_id:
            raise ScheduleOwnershipError("You are not the creator of this schedule")

        # If partner_ids changed, validate them
        if data.partner_ids is not None:
            self._validate_partners(user_id, data.partner_ids)

        # Build partial update dict (only non-None fields)
        update_fields: dict = {}
        if data.partner_ids is not None:
            update_fields["partner_ids"] = data.partner_ids
        if data.days_of_week is not None:
            update_fields["days_of_week"] = data.days_of_week
        if data.slot_time is not None:
            update_fields["slot_time"] = data.slot_time.strftime("%H:%M:%S")
        if data.timezone is not None:
            update_fields["timezone"] = data.timezone
        if data.label is not None:
            update_fields["label"] = data.label
        if data.table_mode is not None:
            update_fields["table_mode"] = data.table_mode
        if data.max_seats is not None:
            update_fields["max_seats"] = data.max_seats
        if data.fill_ai is not None:
            update_fields["fill_ai"] = data.fill_ai
        if data.topic is not None:
            update_fields["topic"] = data.topic
        if data.is_active is not None:
            update_fields["is_active"] = data.is_active

        if not update_fields:
            return self._schedule_to_info(schedule)

        update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

        updated_result = (
            self.supabase.table("recurring_schedules")
            .update(update_fields)
            .eq("id", schedule_id)
            .execute()
        )

        if not updated_result.data:
            raise ScheduleNotFoundError(f"Failed to update schedule {schedule_id}")

        logger.info("Updated recurring schedule %s", schedule_id)
        return self._schedule_to_info(updated_result.data[0])

    def delete_schedule(self, schedule_id: str, user_id: str) -> None:
        """
        Delete a recurring schedule.

        Args:
            schedule_id: UUID of the schedule to delete
            user_id: UUID of the requesting user

        Raises:
            ScheduleNotFoundError: Schedule does not exist
            ScheduleOwnershipError: User is not the creator
        """
        result = (
            self.supabase.table("recurring_schedules")
            .select("id, creator_id")
            .eq("id", schedule_id)
            .execute()
        )

        if not result.data:
            raise ScheduleNotFoundError(f"Schedule {schedule_id} not found")

        if result.data[0]["creator_id"] != user_id:
            raise ScheduleOwnershipError("You are not the creator of this schedule")

        self.supabase.table("recurring_schedules").delete().eq("id", schedule_id).execute()

        logger.info("Deleted recurring schedule %s", schedule_id)

    # =========================================================================
    # Automated Session Creation (Celery Beat)
    # =========================================================================

    def create_scheduled_sessions(self, lookahead_hours: int = SCHEDULE_LOOKAHEAD_HOURS) -> dict:
        """
        Create sessions from active recurring schedules.

        Called periodically by Celery beat. For each active schedule:
        1. Check if today matches a scheduled day_of_week
        2. Convert slot_time to UTC
        3. Skip if outside the lookahead window
        4. Skip if session already exists for this schedule + time
        5. Create private session with invitations

        Args:
            lookahead_hours: How far ahead to look for due schedules

        Returns:
            Summary dict with sessions_created and invitations_sent counts
        """
        now = datetime.now(timezone.utc)
        lookahead_end = now + timedelta(hours=lookahead_hours)

        sessions_created = 0
        invitations_sent = 0

        # Fetch all active schedules
        result = (
            self.supabase.table("recurring_schedules").select("*").eq("is_active", True).execute()
        )

        schedules = result.data or []
        logger.info(
            "Processing %d active recurring schedules (lookahead=%dh)",
            len(schedules),
            lookahead_hours,
        )

        for schedule in schedules:
            try:
                created, invited = self._process_schedule(schedule, now, lookahead_end)
                sessions_created += created
                invitations_sent += invited
            except Exception:
                logger.exception("Error processing schedule %s", schedule.get("id"))

        logger.info(
            "Schedule processing complete: %d sessions created, %d invitations sent",
            sessions_created,
            invitations_sent,
        )

        return {
            "sessions_created": sessions_created,
            "invitations_sent": invitations_sent,
        }

    def _process_schedule(
        self,
        schedule: dict,
        now: datetime,
        lookahead_end: datetime,
    ) -> tuple[int, int]:
        """
        Process a single recurring schedule.

        Returns:
            Tuple of (sessions_created, invitations_sent)
        """
        schedule_id = schedule["id"]
        creator_id = schedule["creator_id"]
        days_of_week = schedule.get("days_of_week") or []
        slot_time_raw = schedule.get("slot_time", "00:00:00")
        tz_name = schedule.get("timezone", "Asia/Taipei")

        # Parse slot_time string to time object
        slot_time_parts = slot_time_raw.split(":")
        slot_time_parsed = time(
            hour=int(slot_time_parts[0]),
            minute=int(slot_time_parts[1]),
            second=int(slot_time_parts[2]) if len(slot_time_parts) > 2 else 0,
        )

        local_tz = ZoneInfo(tz_name)

        # Check today and tomorrow in the schedule's local timezone
        # (to handle timezone edge cases near midnight)
        local_now = now.astimezone(local_tz)
        sessions_created = 0
        invitations_sent = 0

        for day_offset in range(2):  # today and tomorrow
            check_date = (local_now + timedelta(days=day_offset)).date()
            check_weekday = check_date.isoweekday() % 7  # Convert to 0=Sun format

            if check_weekday not in days_of_week:
                continue

            # Combine date + slot_time in local timezone, then convert to UTC
            local_dt = datetime.combine(check_date, slot_time_parsed, tzinfo=local_tz)
            utc_dt = local_dt.astimezone(timezone.utc)

            # Check if within lookahead window (and not in the past)
            if utc_dt <= now or utc_dt > lookahead_end:
                continue

            # Check for existing session with this schedule + start_time
            existing = (
                self.supabase.table("sessions")
                .select("id")
                .eq("recurring_schedule_id", schedule_id)
                .eq("start_time", utc_dt.isoformat())
                .execute()
            )

            if existing.data:
                continue  # Session already created

            # Create the private session
            created, invited = self._create_private_session(
                schedule, utc_dt, creator_id, schedule_id
            )
            sessions_created += created
            invitations_sent += invited

        return sessions_created, invitations_sent

    def _create_private_session(
        self,
        schedule: dict,
        start_time: datetime,
        creator_id: str,
        schedule_id: str,
    ) -> tuple[int, int]:
        """
        Create a private session from a schedule and send invitations.

        Returns:
            Tuple of (1 if session created else 0, number of invitations sent)
        """
        end_time = start_time + timedelta(minutes=SESSION_DURATION_MINUTES)
        room_name = f"private_{schedule_id[:8]}_{start_time.strftime('%Y%m%d_%H%M')}"

        session_data = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "mode": schedule.get("table_mode", "forced_audio"),
            "topic": schedule.get("topic"),
            "current_phase": "setup",
            "livekit_room_name": room_name,
            "is_private": True,
            "created_by": creator_id,
            "recurring_schedule_id": schedule_id,
            "max_seats": schedule.get("max_seats", 4),
        }

        session_result = self.supabase.table("sessions").insert(session_data).execute()

        if not session_result.data:
            logger.error(
                "Failed to create session for schedule %s at %s",
                schedule_id,
                start_time.isoformat(),
            )
            return 0, 0

        session = session_result.data[0]
        session_id = session["id"]

        # Add creator as participant (seat 1)
        self.supabase.table("session_participants").insert(
            {
                "session_id": session_id,
                "user_id": creator_id,
                "participant_type": "human",
                "seat_number": 1,
            }
        ).execute()

        # Create invitations for partners (skip banned users)
        partner_ids = schedule.get("partner_ids") or []
        invitations_sent = 0

        if partner_ids:
            # Check for banned partners
            banned_result = (
                self.supabase.table("users")
                .select("id, banned_until")
                .in_("id", partner_ids)
                .execute()
            )

            banned_users: set[str] = set()
            for user in banned_result.data or []:
                banned_until = user.get("banned_until")
                if banned_until:
                    # Parse banned_until and check if still active
                    if isinstance(banned_until, str):
                        try:
                            ban_dt = datetime.fromisoformat(banned_until.replace("Z", "+00:00"))
                            if ban_dt > datetime.now(timezone.utc):
                                banned_users.add(user["id"])
                        except (ValueError, TypeError):
                            pass

            for partner_id in partner_ids:
                if partner_id in banned_users:
                    logger.info(
                        "Skipping banned partner %s for schedule %s",
                        partner_id,
                        schedule_id,
                    )
                    continue

                invitation_data = {
                    "session_id": session_id,
                    "inviter_id": creator_id,
                    "invitee_id": partner_id,
                    "status": "pending",
                }

                self.supabase.table("table_invitations").insert(invitation_data).execute()
                invitations_sent += 1

        logger.info(
            "Created private session %s from schedule %s (start=%s, invitations=%d)",
            session_id,
            schedule_id,
            start_time.isoformat(),
            invitations_sent,
        )

        return 1, invitations_sent
