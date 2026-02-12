"""
Weekly session streak service.

Manages session count tracking per week and awards bonus essence
at configured thresholds (3 sessions = +1, 5 sessions = +2).
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from supabase import Client

from app.core.constants import STREAK_BONUS_THRESHOLDS
from app.core.database import get_supabase
from app.models.gamification import StreakBonusResult, WeeklyStreakResponse

logger = logging.getLogger(__name__)


class StreakService:
    """Service for weekly session streaks and bonus essence awards."""

    def __init__(self, supabase: Optional[Client] = None):
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    def get_weekly_streak(self, user_id: str) -> WeeklyStreakResponse:
        """Get current week's session count and bonus status."""
        week_start = self._get_current_week_start()

        result = (
            self.supabase.table("weekly_streaks")
            .select("session_count, week_start, bonus_3_awarded, bonus_5_awarded")
            .eq("user_id", user_id)
            .eq("week_start", week_start.isoformat())
            .execute()
        )

        if not result.data:
            return WeeklyStreakResponse(
                session_count=0,
                week_start=week_start,
                next_bonus_at=3,
                bonus_3_awarded=False,
                bonus_5_awarded=False,
                total_bonus_earned=0,
            )

        row = result.data[0]
        bonus_3 = row["bonus_3_awarded"]
        bonus_5 = row["bonus_5_awarded"]

        return WeeklyStreakResponse(
            session_count=row["session_count"],
            week_start=date.fromisoformat(row["week_start"]),
            next_bonus_at=self._compute_next_bonus_at(bonus_3, bonus_5),
            bonus_3_awarded=bonus_3,
            bonus_5_awarded=bonus_5,
            total_bonus_earned=self._compute_total_bonus(bonus_3, bonus_5),
        )

    def increment_session_count(self, user_id: str) -> Optional[StreakBonusResult]:
        """
        Increment the weekly session count after a completed session.

        Uses upsert with ON CONFLICT(user_id, week_start) for atomicity —
        safe against concurrent webhook calls for the same user.

        Awards bonus essence if a threshold is crossed.
        Returns StreakBonusResult if bonus awarded, None otherwise.
        """
        week_start = self._get_current_week_start()
        now = datetime.now(timezone.utc).isoformat()

        # Fetch current row (if exists) to get current count + flags
        fetch = (
            self.supabase.table("weekly_streaks")
            .select("*")
            .eq("user_id", user_id)
            .eq("week_start", week_start.isoformat())
            .execute()
        )

        if fetch.data:
            row = fetch.data[0]
            new_count = row["session_count"] + 1
            bonus_3 = row["bonus_3_awarded"]
            bonus_5 = row["bonus_5_awarded"]
        else:
            new_count = 1
            bonus_3 = False
            bonus_5 = False

        # Atomic upsert — ON CONFLICT(user_id, week_start) updates count
        upsert_result = (
            self.supabase.table("weekly_streaks")
            .upsert(
                {
                    "user_id": user_id,
                    "week_start": week_start.isoformat(),
                    "session_count": new_count,
                    "bonus_3_awarded": bonus_3,
                    "bonus_5_awarded": bonus_5,
                    "updated_at": now,
                },
                on_conflict="user_id,week_start",
            )
            .execute()
        )
        row_id = upsert_result.data[0]["id"] if upsert_result.data else None

        # Check each threshold in order
        for threshold in STREAK_BONUS_THRESHOLDS:
            sessions_needed = threshold["sessions"]
            bonus_amount = threshold["bonus_essence"]
            flag_name = threshold["flag"]
            flag_value = bonus_3 if flag_name == "bonus_3_awarded" else bonus_5

            if new_count >= sessions_needed and not flag_value:
                # Award bonus essence
                new_balance = self._award_bonus_essence(user_id, bonus_amount)

                # Set the flag
                if row_id:
                    self.supabase.table("weekly_streaks").update(
                        {flag_name: True, "updated_at": now}
                    ).eq("id", row_id).execute()

                return StreakBonusResult(
                    bonus_essence=bonus_amount,
                    threshold_reached=sessions_needed,
                    new_balance=new_balance,
                )

        return None

    def _award_bonus_essence(self, user_id: str, amount: int) -> int:
        """Award bonus essence and log transaction. Returns new balance."""
        now = datetime.now(timezone.utc).isoformat()

        # Fetch current balance first, then add — never overwrite
        essence_result = (
            self.supabase.table("furniture_essence")
            .select("balance, total_earned")
            .eq("user_id", user_id)
            .execute()
        )

        if not essence_result.data:
            logger.warning(f"No furniture_essence row for user {user_id}")
            return 0

        current = essence_result.data[0]
        new_balance = current["balance"] + amount
        new_total = current["total_earned"] + amount

        self.supabase.table("furniture_essence").update(
            {
                "balance": new_balance,
                "total_earned": new_total,
                "updated_at": now,
            }
        ).eq("user_id", user_id).execute()

        self.supabase.table("essence_transactions").insert(
            {
                "user_id": user_id,
                "amount": amount,
                "transaction_type": "streak_bonus",
            }
        ).execute()

        return new_balance

    def _get_current_week_start(self) -> date:
        """Return Monday of the current ISO week (UTC)."""
        today = datetime.now(timezone.utc).date()
        return today - timedelta(days=today.weekday())

    @staticmethod
    def _compute_next_bonus_at(bonus_3: bool, bonus_5: bool) -> int:
        """Compute the next bonus threshold to display."""
        if not bonus_3:
            return 3
        if not bonus_5:
            return 5
        return 5

    @staticmethod
    def _compute_total_bonus(bonus_3: bool, bonus_5: bool) -> int:
        """Compute total bonus essence earned this week."""
        total = 0
        if bonus_3:
            total += 1
        if bonus_5:
            total += 2
        return total
