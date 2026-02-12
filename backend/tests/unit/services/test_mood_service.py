"""Unit tests for MoodService (TDD — written before implementation).

Tests:
- compute_mood() - positive, tired, neutral, no data
- get_reaction_for_tags() - maps tag to reaction, no active companion, multiple tags
"""

from unittest.mock import MagicMock

import pytest

from app.models.gamification import CompanionReactionResponse, MoodResponse
from app.services.mood_service import MoodService


@pytest.fixture
def mock_supabase():
    return MagicMock()


@pytest.fixture
def service(mock_supabase):
    return MoodService(supabase=mock_supabase)


# =============================================================================
# Helpers
# =============================================================================


def _make_table_mock():
    mock = MagicMock()
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.gte.return_value = mock
    mock.execute.return_value = MagicMock(data=[])
    return mock


def _setup_tables(mock_supabase, table_names):
    tables = {}
    for name in table_names:
        tables[name] = _make_table_mock()

    def route(name):
        if name not in tables:
            tables[name] = _make_table_mock()
        return tables[name]

    mock_supabase.table.side_effect = route
    return tables


# =============================================================================
# compute_mood()
# =============================================================================


class TestComputeMood:
    def test_mostly_positive_returns_positive(self, service, mock_supabase):
        """When recent diary tags are mostly positive, mood is 'positive'."""
        tables = _setup_tables(mock_supabase, ["diary_notes"])
        tables["diary_notes"].execute.return_value = MagicMock(
            data=[
                {"tags": ["productive", "deep-focus"]},
                {"tags": ["energized"]},
                {"tags": ["breakthrough"]},
            ]
        )

        result = service.compute_mood("user-1")

        assert isinstance(result, MoodResponse)
        assert result.mood == "positive"
        assert result.positive_count == 4
        assert result.negative_count == 0
        assert result.score > 0.3

    def test_mostly_negative_returns_tired(self, service, mock_supabase):
        """When recent diary tags are mostly negative, mood is 'tired'."""
        tables = _setup_tables(mock_supabase, ["diary_notes"])
        tables["diary_notes"].execute.return_value = MagicMock(
            data=[
                {"tags": ["tired", "distracted"]},
                {"tags": ["struggled"]},
                {"tags": ["tired"]},
            ]
        )

        result = service.compute_mood("user-1")

        assert result.mood == "tired"
        assert result.negative_count == 4
        assert result.score < -0.3

    def test_mixed_returns_neutral(self, service, mock_supabase):
        """When recent diary tags are mixed, mood is 'neutral'."""
        tables = _setup_tables(mock_supabase, ["diary_notes"])
        tables["diary_notes"].execute.return_value = MagicMock(
            data=[
                {"tags": ["productive", "tired"]},
                {"tags": ["energized", "distracted"]},
            ]
        )

        result = service.compute_mood("user-1")

        assert result.mood == "neutral"

    def test_no_diary_entries_returns_neutral(self, service, mock_supabase):
        """When no diary entries exist, mood is 'neutral' with score 0."""
        tables = _setup_tables(mock_supabase, ["diary_notes"])
        tables["diary_notes"].execute.return_value = MagicMock(data=[])

        result = service.compute_mood("user-1")

        assert result.mood == "neutral"
        assert result.score == 0.0
        assert result.total_count == 0


# =============================================================================
# get_reaction_for_tags()
# =============================================================================


class TestGetReactionForTags:
    def test_maps_tag_to_reaction(self, service, mock_supabase):
        """Returns companion reaction matching the first diary tag."""
        tables = _setup_tables(mock_supabase, ["user_room"])
        tables["user_room"].execute.return_value = MagicMock(data=[{"active_companion": "cat"}])

        result = service.get_reaction_for_tags("user-1", ["breakthrough"])

        assert isinstance(result, CompanionReactionResponse)
        assert result.companion_type == "cat"
        assert result.animation == "reaction-jump"
        assert result.tag == "breakthrough"

    def test_no_active_companion_returns_none(self, service, mock_supabase):
        """When user has no active companion, returns None."""
        tables = _setup_tables(mock_supabase, ["user_room"])
        tables["user_room"].execute.return_value = MagicMock(data=[])

        result = service.get_reaction_for_tags("user-1", ["productive"])

        assert result is None

    def test_no_companion_set_returns_none(self, service, mock_supabase):
        """When active_companion is null, returns None."""
        tables = _setup_tables(mock_supabase, ["user_room"])
        tables["user_room"].execute.return_value = MagicMock(data=[{"active_companion": None}])

        result = service.get_reaction_for_tags("user-1", ["productive"])

        assert result is None

    def test_multiple_tags_picks_first_match(self, service, mock_supabase):
        """When multiple tags provided, returns reaction for the first matching one."""
        tables = _setup_tables(mock_supabase, ["user_room"])
        tables["user_room"].execute.return_value = MagicMock(data=[{"active_companion": "dog"}])

        result = service.get_reaction_for_tags("user-1", ["tired", "breakthrough"])

        assert result is not None
        assert result.tag == "tired"
        assert result.animation == "reaction-nap"

    def test_no_matching_tags_returns_none(self, service, mock_supabase):
        """When tags don't have reactions, returns None."""
        tables = _setup_tables(mock_supabase, ["user_room"])
        tables["user_room"].execute.return_value = MagicMock(data=[{"active_companion": "cat"}])

        result = service.get_reaction_for_tags("user-1", ["unknown-tag"])

        assert result is None

    def test_empty_tags_returns_none(self, service, mock_supabase):
        """When no tags provided, returns None."""
        tables = _setup_tables(mock_supabase, ["user_room"])
        tables["user_room"].execute.return_value = MagicMock(data=[{"active_companion": "cat"}])

        result = service.get_reaction_for_tags("user-1", [])

        assert result is None
