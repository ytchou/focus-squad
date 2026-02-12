"""Unit tests for schedules router endpoints.

Tests:
- GET / - list_schedules: List user's recurring schedules
- POST / - create_schedule: Create a recurring schedule (Unlimited plan only)
- PATCH /{id} - update_schedule: Update a recurring schedule
- DELETE /{id} - delete_schedule: Delete a recurring schedule
- Error handling: SchedulePermissionError returns 403
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

PREFIX = "/api/v1/schedules"


def _make_schedule_info(**overrides) -> dict:
    """Helper to build a schedule info dict with sensible defaults."""
    defaults = {
        "id": "schedule-uuid-001",
        "label": "Morning Study",
        "creator_id": "test-user-uuid",
        "partner_ids": ["partner-uuid-1"],
        "partner_names": ["Study Buddy"],
        "days_of_week": [1, 3, 5],
        "slot_time": "09:00",
        "timezone": "Asia/Taipei",
        "table_mode": "forced_audio",
        "max_seats": 4,
        "fill_ai": True,
        "topic": None,
        "is_active": True,
        "created_at": "2025-01-01T00:00:00Z",
    }
    defaults.update(overrides)
    return defaults


@pytest.fixture
def mock_auth_user():
    """Create a mock AuthUser with user_id attribute."""
    user = MagicMock()
    user.user_id = "test-user-uuid"
    user.auth_id = "test-auth-id"
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_schedule_service():
    """Create a mock ScheduleService."""
    return MagicMock()


@pytest.fixture
def client(mock_auth_user, mock_schedule_service):
    """Create test client with mocked auth and schedule service."""
    from app.core.auth import require_auth_from_state
    from app.main import app
    from app.routers.schedules import get_schedule_service

    app.dependency_overrides[require_auth_from_state] = lambda: mock_auth_user
    app.dependency_overrides[get_schedule_service] = lambda: mock_schedule_service

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


# =============================================================================
# GET / - list_schedules
# =============================================================================


class TestListSchedules:
    """Tests for GET /api/v1/schedules/."""

    @pytest.mark.unit
    def test_list_schedules_success(self, client, mock_schedule_service):
        """Returns 200 with empty schedule list."""
        mock_schedule_service.list_schedules.return_value = []

        response = client.get(f"{PREFIX}/")

        assert response.status_code == 200
        data = response.json()
        assert data["schedules"] == []
        mock_schedule_service.list_schedules.assert_called_once_with("test-user-uuid")

    @pytest.mark.unit
    def test_list_schedules_with_data(self, client, mock_schedule_service):
        """Returns schedule data when schedules exist."""
        schedule = _make_schedule_info()
        mock_schedule_service.list_schedules.return_value = [schedule]

        response = client.get(f"{PREFIX}/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["schedules"]) == 1
        assert data["schedules"][0]["id"] == "schedule-uuid-001"
        assert data["schedules"][0]["label"] == "Morning Study"
        assert data["schedules"][0]["days_of_week"] == [1, 3, 5]


# =============================================================================
# POST / - create_schedule
# =============================================================================


class TestCreateSchedule:
    """Tests for POST /api/v1/schedules/."""

    @pytest.mark.unit
    def test_create_schedule_success(self, client, mock_schedule_service):
        """Returns 201 with created schedule."""
        schedule = _make_schedule_info()
        mock_schedule_service.create_schedule.return_value = schedule

        response = client.post(
            f"{PREFIX}/",
            json={
                "partner_ids": ["partner-uuid-1"],
                "days_of_week": [1, 3, 5],
                "slot_time": "09:00:00",
                "timezone": "Asia/Taipei",
                "label": "Morning Study",
                "table_mode": "forced_audio",
                "max_seats": 4,
                "fill_ai": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["schedule"]["id"] == "schedule-uuid-001"
        assert data["schedule"]["label"] == "Morning Study"
        mock_schedule_service.create_schedule.assert_called_once()

    @pytest.mark.unit
    def test_create_schedule_permission_error(self, client, mock_schedule_service):
        """Returns 403 when user is not on Unlimited plan."""
        from app.models.schedule import SchedulePermissionError

        mock_schedule_service.create_schedule.side_effect = SchedulePermissionError(
            "Recurring schedules require the Unlimited plan"
        )

        response = client.post(
            f"{PREFIX}/",
            json={
                "partner_ids": ["partner-uuid-1"],
                "days_of_week": [1],
                "slot_time": "10:00:00",
            },
        )

        assert response.status_code == 403
        assert response.json()["code"] == "SCHEDULE_PERMISSION"

    @pytest.mark.unit
    def test_create_schedule_limit_error(self, client, mock_schedule_service):
        """Returns 429 when max schedules reached."""
        from app.models.schedule import ScheduleLimitError

        mock_schedule_service.create_schedule.side_effect = ScheduleLimitError(
            "Maximum recurring schedules reached"
        )

        response = client.post(
            f"{PREFIX}/",
            json={
                "partner_ids": ["partner-uuid-1"],
                "days_of_week": [0],
                "slot_time": "14:00:00",
            },
        )

        assert response.status_code == 429
        assert response.json()["code"] == "SCHEDULE_LIMIT_EXCEEDED"

    @pytest.mark.unit
    def test_create_schedule_missing_body_returns_422(self, client, mock_schedule_service):
        """Returns 422 when request body is missing."""
        response = client.post(f"{PREFIX}/")

        assert response.status_code == 422

    @pytest.mark.unit
    def test_create_schedule_invalid_day_returns_422(self, client, mock_schedule_service):
        """Returns 422 when day_of_week value is out of range."""
        response = client.post(
            f"{PREFIX}/",
            json={
                "partner_ids": ["partner-uuid-1"],
                "days_of_week": [9],
                "slot_time": "10:00:00",
            },
        )

        assert response.status_code == 422


# =============================================================================
# PATCH /{schedule_id} - update_schedule
# =============================================================================


class TestUpdateSchedule:
    """Tests for PATCH /api/v1/schedules/{id}."""

    @pytest.mark.unit
    def test_update_schedule_success(self, client, mock_schedule_service):
        """Returns 200 with updated schedule."""
        updated = _make_schedule_info(label="Evening Study", days_of_week=[2, 4])
        mock_schedule_service.update_schedule.return_value = updated

        response = client.patch(
            f"{PREFIX}/schedule-uuid-001",
            json={"label": "Evening Study", "days_of_week": [2, 4]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["schedule"]["label"] == "Evening Study"
        assert data["schedule"]["days_of_week"] == [2, 4]
        mock_schedule_service.update_schedule.assert_called_once()
        call_args = mock_schedule_service.update_schedule.call_args
        assert call_args[0][0] == "schedule-uuid-001"
        assert call_args[0][1] == "test-user-uuid"

    @pytest.mark.unit
    def test_update_schedule_not_found(self, client, mock_schedule_service):
        """Returns 404 when schedule does not exist."""
        from app.models.schedule import ScheduleNotFoundError

        mock_schedule_service.update_schedule.side_effect = ScheduleNotFoundError(
            "Schedule not found"
        )

        response = client.patch(
            f"{PREFIX}/nonexistent",
            json={"label": "Updated"},
        )

        assert response.status_code == 404
        assert response.json()["code"] == "SCHEDULE_NOT_FOUND"

    @pytest.mark.unit
    def test_update_schedule_ownership_error(self, client, mock_schedule_service):
        """Returns 403 when user is not the schedule creator."""
        from app.models.schedule import ScheduleOwnershipError

        mock_schedule_service.update_schedule.side_effect = ScheduleOwnershipError(
            "You are not the creator of this schedule"
        )

        response = client.patch(
            f"{PREFIX}/other-users-schedule",
            json={"label": "Hijacked"},
        )

        assert response.status_code == 403
        assert response.json()["code"] == "SCHEDULE_OWNERSHIP"

    @pytest.mark.unit
    def test_update_schedule_toggle_active(self, client, mock_schedule_service):
        """Returns 200 when toggling is_active flag."""
        updated = _make_schedule_info(is_active=False)
        mock_schedule_service.update_schedule.return_value = updated

        response = client.patch(
            f"{PREFIX}/schedule-uuid-001",
            json={"is_active": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["schedule"]["is_active"] is False


# =============================================================================
# DELETE /{schedule_id} - delete_schedule
# =============================================================================


class TestDeleteSchedule:
    """Tests for DELETE /api/v1/schedules/{id}."""

    @pytest.mark.unit
    def test_delete_schedule_success(self, client, mock_schedule_service):
        """Returns 200 with success message."""
        mock_schedule_service.delete_schedule.return_value = None

        response = client.delete(f"{PREFIX}/schedule-uuid-001")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Schedule deleted"
        mock_schedule_service.delete_schedule.assert_called_once_with(
            "schedule-uuid-001", "test-user-uuid"
        )

    @pytest.mark.unit
    def test_delete_schedule_not_found(self, client, mock_schedule_service):
        """Returns 404 when schedule does not exist."""
        from app.models.schedule import ScheduleNotFoundError

        mock_schedule_service.delete_schedule.side_effect = ScheduleNotFoundError(
            "Schedule not found"
        )

        response = client.delete(f"{PREFIX}/nonexistent")

        assert response.status_code == 404
        assert response.json()["code"] == "SCHEDULE_NOT_FOUND"

    @pytest.mark.unit
    def test_delete_schedule_ownership_error(self, client, mock_schedule_service):
        """Returns 403 when user is not the schedule creator."""
        from app.models.schedule import ScheduleOwnershipError

        mock_schedule_service.delete_schedule.side_effect = ScheduleOwnershipError(
            "You are not the creator of this schedule"
        )

        response = client.delete(f"{PREFIX}/other-users-schedule")

        assert response.status_code == 403
        assert response.json()["code"] == "SCHEDULE_OWNERSHIP"


# =============================================================================
# Authentication
# =============================================================================


class TestSchedulesAuth:
    """Tests that endpoints require authentication."""

    @pytest.fixture
    def unauthenticated_client(self):
        """Create test client without auth overrides."""
        from app.main import app

        app.dependency_overrides.clear()

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

        app.dependency_overrides.clear()

    @pytest.mark.unit
    def test_list_schedules_requires_auth(self, unauthenticated_client):
        """GET / returns 401 without authentication."""
        response = unauthenticated_client.get(f"{PREFIX}/")
        assert response.status_code == 401

    @pytest.mark.unit
    def test_create_schedule_requires_auth(self, unauthenticated_client):
        """POST / returns 401 without authentication."""
        response = unauthenticated_client.post(
            f"{PREFIX}/",
            json={
                "partner_ids": ["p1"],
                "days_of_week": [1],
                "slot_time": "09:00:00",
            },
        )
        assert response.status_code == 401

    @pytest.mark.unit
    def test_update_schedule_requires_auth(self, unauthenticated_client):
        """PATCH /{id} returns 401 without authentication."""
        response = unauthenticated_client.patch(
            f"{PREFIX}/some-id",
            json={"label": "Updated"},
        )
        assert response.status_code == 401

    @pytest.mark.unit
    def test_delete_schedule_requires_auth(self, unauthenticated_client):
        """DELETE /{id} returns 401 without authentication."""
        response = unauthenticated_client.delete(f"{PREFIX}/some-id")
        assert response.status_code == 401
