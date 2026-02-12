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

        Fetch-then-upsert pattern: read current row, increment in Python,
        write back via upsert. Concurrent calls are serialized by the
        webhook handler (one session completion at a time).

        Awards bonus essence if a threshold is crossed.
        Returns StreakBonusResult if bonus awarded, None otherwise.
        """
        week_start = self._get_current_week_start()
        now = datetime.now(timezone.utc).isoformat()

        # Fetch current row
        fetch = (
            self.supabase.table("weekly_streaks")
            .select("*")
            .eq("user_id", user_id)
            .eq("week_start", week_start.isoformat())
            .execute()
        )

        if fetch.data:
            # Existing row: increment count
            row = fetch.data[0]
            new_count = row["session_count"] + 1

            self.supabase.table("weekly_streaks").update(
                {"session_count": new_count, "updated_at": now}
            ).eq("id", row["id"]).execute()

            bonus_3 = row["bonus_3_awarded"]
            bonus_5 = row["bonus_5_awarded"]
            row_id = row["id"]
        else:
            # New row: insert with count=1
            insert_result = (
                self.supabase.table("weekly_streaks")
                .insert(
                    {
                        "user_id": user_id,
                        "week_start": week_start.isoformat(),
                        "session_count": 1,
                        "bonus_3_awarded": False,
                        "bonus_5_awarded": False,
                        "updated_at": now,
                    }
                )
                .execute()
            )
            new_count = 1
            bonus_3 = False
            bonus_5 = False
            row_id = insert_result.data[0]["id"] if insert_result.data else None

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
        result = (
            self.supabase.table("furniture_essence")
            .update(
                {
                    "balance": amount,
                    "total_earned": amount,
                }
            )
            .eq("user_id", user_id)
            .execute()
        )

        new_balance = result.data[0]["balance"] if result.data else 0

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
