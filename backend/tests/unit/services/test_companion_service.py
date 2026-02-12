"""Unit tests for CompanionService.

Tests:
- get_companions() - returns list, empty list
- has_starter() - true when exists, false when not
- choose_starter() - happy path, invalid type, already has starter
- adopt_visitor() - happy path, visitor not found
- get_companion_metadata() - known type, unknown type
"""

from unittest.mock import MagicMock

import pytest

from app.models.room import (
    AlreadyHasStarterError,
    CompanionInfo,
    CompanionServiceError,
    InvalidStarterError,
    VisitorNotFoundError,
)
from app.services.companion_service import CompanionService


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    return MagicMock()


@pytest.fixture
def service(mock_supabase):
    """CompanionService with mocked Supabase."""
    return CompanionService(supabase=mock_supabase)


# =============================================================================
# Helpers
# =============================================================================


def _make_table_mock():
    """Create a chainable table mock."""
    mock = MagicMock()
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.is_.return_value = mock
    mock.order.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.execute.return_value = MagicMock(data=[])
    return mock


def _setup_tables(mock_supabase, table_names):
    """Configure table-specific mock routing with pre-populated table mocks."""
    tables = {}
    for name in table_names:
        tables[name] = _make_table_mock()

    def route(name):
        if name not in tables:
            tables[name] = _make_table_mock()
        return tables[name]

    mock_supabase.table.side_effect = route
    return tables


def _sample_companion(
    comp_id="comp-1",
    user_id="user-123",
    companion_type="cat",
    is_starter=True,
    adopted_at="2026-02-01T00:00:00Z",
):
    """Sample user_companions row."""
    return {
        "id": comp_id,
        "user_id": user_id,
        "companion_type": companion_type,
        "is_starter": is_starter,
        "discovered_at": None,
        "visit_scheduled_at": None,
        "adopted_at": adopted_at,
    }


def _sample_visitor(
    comp_id="comp-v1",
    user_id="user-123",
    companion_type="owl",
):
    """Sample unadopted visitor row."""
    return {
        "id": comp_id,
        "user_id": user_id,
        "companion_type": companion_type,
        "is_starter": False,
        "discovered_at": "2026-02-10T00:00:00Z",
        "visit_scheduled_at": "2026-02-10T12:00:00Z",
        "adopted_at": None,
    }


# =============================================================================
# TestGetCompanions
# =============================================================================


class TestGetCompanions:
    """Tests for get_companions() method."""

    @pytest.mark.unit
    def test_returns_list(self, service, mock_supabase) -> None:
        """Returns list of CompanionInfo for user."""
        tables = _setup_tables(mock_supabase, ["user_companions"])
        companions = [
            _sample_companion(comp_id="c-1", companion_type="cat"),
            _sample_companion(comp_id="c-2", companion_type="owl", is_starter=False),
        ]
        tables["user_companions"].execute.return_value = MagicMock(data=companions)

        result = service.get_companions("user-123")

        assert len(result) == 2
        assert all(isinstance(c, CompanionInfo) for c in result)
        assert result[0].companion_type == "cat"
        assert result[1].companion_type == "owl"

    @pytest.mark.unit
    def test_returns_empty_list(self, service, mock_supabase) -> None:
        """Returns empty list when user has no companions."""
        tables = _setup_tables(mock_supabase, ["user_companions"])
        tables["user_companions"].execute.return_value = MagicMock(data=[])

        result = service.get_companions("user-123")

        assert result == []


# =============================================================================
# TestHasStarter
# =============================================================================


class TestHasStarter:
    """Tests for has_starter() method."""

    @pytest.mark.unit
    def test_true_when_starter_exists(self, service, mock_supabase) -> None:
        """Returns True when user has a starter companion."""
        tables = _setup_tables(mock_supabase, ["user_companions"])
        tables["user_companions"].execute.return_value = MagicMock(data=[{"id": "comp-1"}])

        result = service.has_starter("user-123")

        assert result is True

    @pytest.mark.unit
    def test_false_when_no_starter(self, service, mock_supabase) -> None:
        """Returns False when user has no starter companion."""
        tables = _setup_tables(mock_supabase, ["user_companions"])
        tables["user_companions"].execute.return_value = MagicMock(data=[])

        result = service.has_starter("user-123")

        assert result is False


# =============================================================================
# TestChooseStarter
# =============================================================================


class TestChooseStarter:
    """Tests for choose_starter() method."""

    @pytest.mark.unit
    def test_happy_path(self, service, mock_supabase) -> None:
        """Successfully creates starter companion."""
        tables = _setup_tables(mock_supabase, ["user_companions"])

        # has_starter returns False (first execute), insert returns new row (second execute)
        execute_results = [
            MagicMock(data=[]),  # has_starter check
            MagicMock(data=[_sample_companion(companion_type="dog")]),  # insert
        ]
        tables["user_companions"].execute.side_effect = execute_results

        result = service.choose_starter("user-123", "dog")

        assert isinstance(result, CompanionInfo)
        assert result.companion_type == "dog"
        assert result.is_starter is True

        # Verify insert data
        tables["user_companions"].insert.assert_called_once()
        insert_data = tables["user_companions"].insert.call_args.args[0]
        assert insert_data["user_id"] == "user-123"
        assert insert_data["companion_type"] == "dog"
        assert insert_data["is_starter"] is True
        assert "adopted_at" in insert_data

    @pytest.mark.unit
    def test_invalid_type_raises_error(self, service, mock_supabase) -> None:
        """Raises InvalidStarterError for non-starter companion types."""
        with pytest.raises(InvalidStarterError, match="not a valid starter"):
            service.choose_starter("user-123", "owl")

    @pytest.mark.unit
    def test_invalid_type_dragon(self, service, mock_supabase) -> None:
        """Raises InvalidStarterError for completely unknown type."""
        with pytest.raises(InvalidStarterError, match="not a valid starter"):
            service.choose_starter("user-123", "dragon")

    @pytest.mark.unit
    def test_already_has_starter_raises_error(self, service, mock_supabase) -> None:
        """Raises AlreadyHasStarterError when user already chose a starter."""
        tables = _setup_tables(mock_supabase, ["user_companions"])
        # has_starter returns True
        tables["user_companions"].execute.return_value = MagicMock(data=[{"id": "comp-existing"}])

        with pytest.raises(AlreadyHasStarterError, match="already has a starter"):
            service.choose_starter("user-123", "cat")

    @pytest.mark.unit
    def test_insert_fails_raises_error(self, service, mock_supabase) -> None:
        """Raises CompanionServiceError when insert returns empty data."""
        tables = _setup_tables(mock_supabase, ["user_companions"])

        execute_results = [
            MagicMock(data=[]),  # has_starter check (no starter)
            MagicMock(data=[]),  # insert fails (empty data)
        ]
        tables["user_companions"].execute.side_effect = execute_results

        with pytest.raises(CompanionServiceError, match="Failed to create"):
            service.choose_starter("user-123", "bunny")


# =============================================================================
# TestAdoptVisitor
# =============================================================================


class TestAdoptVisitor:
    """Tests for adopt_visitor() method."""

    @pytest.mark.unit
    def test_happy_path(self, service, mock_supabase) -> None:
        """Successfully adopts visiting companion."""
        tables = _setup_tables(mock_supabase, ["user_companions"])

        visitor = _sample_visitor(companion_type="owl")
        adopted = {**visitor, "adopted_at": "2026-02-12T00:00:00Z"}

        execute_results = [
            MagicMock(data=[visitor]),  # select unadopted visitor
            MagicMock(data=[adopted]),  # update adopted_at
        ]
        tables["user_companions"].execute.side_effect = execute_results

        result = service.adopt_visitor("user-123", "owl")

        assert isinstance(result, CompanionInfo)
        assert result.companion_type == "owl"
        assert result.adopted_at is not None

        # Verify update was called with adopted_at
        tables["user_companions"].update.assert_called_once()
        update_data = tables["user_companions"].update.call_args.args[0]
        assert "adopted_at" in update_data

    @pytest.mark.unit
    def test_visitor_not_found_raises_error(self, service, mock_supabase) -> None:
        """Raises VisitorNotFoundError when no unadopted visitor found."""
        tables = _setup_tables(mock_supabase, ["user_companions"])
        tables["user_companions"].execute.return_value = MagicMock(data=[])

        with pytest.raises(VisitorNotFoundError, match="No visiting fox found"):
            service.adopt_visitor("user-123", "fox")

    @pytest.mark.unit
    def test_adopt_update_fails_raises_error(self, service, mock_supabase) -> None:
        """Raises CompanionServiceError when update returns empty data."""
        tables = _setup_tables(mock_supabase, ["user_companions"])

        visitor = _sample_visitor(companion_type="turtle")
        execute_results = [
            MagicMock(data=[visitor]),  # select finds visitor
            MagicMock(data=[]),  # update fails
        ]
        tables["user_companions"].execute.side_effect = execute_results

        with pytest.raises(CompanionServiceError, match="Failed to adopt"):
            service.adopt_visitor("user-123", "turtle")


# =============================================================================
# TestGetCompanionMetadata
# =============================================================================


class TestGetCompanionMetadata:
    """Tests for get_companion_metadata() method."""

    @pytest.mark.unit
    def test_known_starter_type(self, service) -> None:
        """Returns metadata dict for a known starter companion type."""
        result = service.get_companion_metadata("cat")

        assert isinstance(result, dict)
        assert "personality" in result
        assert "preferred_tags" in result
        assert "cozy" in result["preferred_tags"]

    @pytest.mark.unit
    def test_known_discoverable_type(self, service) -> None:
        """Returns metadata dict for a known discoverable companion type."""
        result = service.get_companion_metadata("owl")

        assert isinstance(result, dict)
        assert "personality" in result
        assert "threshold" in result
        assert result["threshold"] == 3
        assert "height" in result["preferred_tags"]

    @pytest.mark.unit
    def test_unknown_type_returns_empty_dict(self, service) -> None:
        """Returns empty dict for unknown companion type."""
        result = service.get_companion_metadata("dragon")

        assert result == {}
