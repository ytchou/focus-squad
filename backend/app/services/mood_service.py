"""
Companion mood service.

Computes mood baseline from recent diary tags and maps diary tags
to companion reaction animations.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from supabase import Client

from app.core.constants import (
    DIARY_TAG_REACTIONS,
    MOOD_NEGATIVE_THRESHOLD,
    MOOD_POSITIVE_THRESHOLD,
    MOOD_WINDOW_DAYS,
    NEGATIVE_DIARY_TAGS,
    POSITIVE_DIARY_TAGS,
)
from app.core.database import get_supabase
from app.models.gamification import CompanionReactionResponse, MoodResponse

logger = logging.getLogger(__name__)


class MoodService:
    """Service for companion mood baseline and diary reactions."""

    def __init__(self, supabase: Optional[Client] = None):
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    def compute_mood(self, user_id: str) -> MoodResponse:
        """
        Analyze last 7 days of diary tags to compute mood baseline.

        Returns mood state (positive/neutral/tired) and score.
        Score = (positive_count - negative_count) / total_count.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=MOOD_WINDOW_DAYS)).isoformat()

        result = (
            self.supabase.table("diary_notes")
            .select("tags")
            .eq("user_id", user_id)
            .gte("created_at", cutoff)
            .execute()
        )

        all_tags = []
        for row in result.data:
            if row.get("tags"):
                all_tags.extend(row["tags"])

        total = len(all_tags)
        if total == 0:
            return MoodResponse(
                mood="neutral",
                score=0.0,
                positive_count=0,
                negative_count=0,
                total_count=0,
            )

        positive_count = sum(1 for t in all_tags if t in POSITIVE_DIARY_TAGS)
        negative_count = sum(1 for t in all_tags if t in NEGATIVE_DIARY_TAGS)
        score = (positive_count - negative_count) / total

        if score > MOOD_POSITIVE_THRESHOLD:
            mood = "positive"
        elif score < MOOD_NEGATIVE_THRESHOLD:
            mood = "tired"
        else:
            mood = "neutral"

        return MoodResponse(
            mood=mood,
            score=score,
            positive_count=positive_count,
            negative_count=negative_count,
            total_count=total,
        )

    def get_reaction_for_tags(
        self, user_id: str, tags: list[str]
    ) -> Optional[CompanionReactionResponse]:
        """
        Given diary tags, determine which companion reaction to play.

        Uses the user's active companion and picks the first matching tag
        that has a reaction animation defined.
        """
        if not tags:
            return None

        # Get user's active companion
        result = (
            self.supabase.table("user_room")
            .select("active_companion")
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data or not result.data[0].get("active_companion"):
            return None

        companion_type = result.data[0]["active_companion"]

        # Find first tag with a reaction
        for tag in tags:
            animation = DIARY_TAG_REACTIONS.get(tag)
            if animation:
                return CompanionReactionResponse(
                    companion_type=companion_type,
                    animation=animation,
                    tag=tag,
                )

        return None
