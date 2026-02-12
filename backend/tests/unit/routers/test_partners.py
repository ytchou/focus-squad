"""Unit tests for partners router endpoints.

Tests:
- GET / - list_partners: List accepted accountability partners
- GET /requests - list_requests: List pending partnership requests
- GET /search?q=test - search_users: Search users by query
- POST /request - send_request: Send a partner request
- POST /request/{id}/respond - respond_to_request: Accept or decline
- DELETE /{id} - remove_partner: Remove a partner
- Auth: Endpoints require authentication
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.models.partner import (
    PartnerListResponse,
    PartnerRemoveResponse,
    PartnerRequestResponse,
    PartnerRequestsResponse,
    PartnerRespondResponse,
    UserSearchResponse,
)

PREFIX = "/api/v1/partners"


@pytest.fixture
def mock_auth_user():
    """Create a mock AuthUser with user_id attribute."""
    user = MagicMock()
    user.user_id = "test-user-uuid"
    user.auth_id = "test-auth-id"
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_partner_service():
    """Create a mock PartnerService."""
    return MagicMock()


@pytest.fixture
def client(mock_auth_user, mock_partner_service):
    """Create test client with mocked auth and partner service."""
    from app.core.auth import require_auth_from_state
    from app.main import app
    from app.routers.partners import get_partner_service

    app.dependency_overrides[require_auth_from_state] = lambda: mock_auth_user
    app.dependency_overrides[get_partner_service] = lambda: mock_partner_service

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


# =============================================================================
# GET / - list_partners
# =============================================================================


class TestListPartners:
    """Tests for GET /api/v1/partners/."""

    @pytest.mark.unit
    def test_list_partners_success(self, client, mock_partner_service):
        """Returns 200 with partner list."""
        mock_partner_service.list_partners.return_value = PartnerListResponse(
            partners=[],
            total=0,
        )

        response = client.get(f"{PREFIX}/")

        assert response.status_code == 200
        data = response.json()
        assert data["partners"] == []
        assert data["total"] == 0
        mock_partner_service.list_partners.assert_called_once_with("test-user-uuid")

    @pytest.mark.unit
    def test_list_partners_with_data(self, client, mock_partner_service):
        """Returns partner data when partners exist."""
        partner_data = {
            "partnership_id": "p-001",
            "user_id": "partner-uuid",
            "username": "studybuddy",
            "display_name": "Study Buddy",
            "avatar_config": {},
            "pixel_avatar_id": None,
            "study_interests": ["math"],
            "reliability_score": "95.00",
            "last_session_together": None,
        }
        mock_partner_service.list_partners.return_value = PartnerListResponse(
            partners=[partner_data],
            total=1,
        )

        response = client.get(f"{PREFIX}/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["partners"]) == 1
        assert data["partners"][0]["username"] == "studybuddy"
        assert data["total"] == 1


# =============================================================================
# GET /requests - list_requests
# =============================================================================


class TestListRequests:
    """Tests for GET /api/v1/partners/requests."""

    @pytest.mark.unit
    def test_list_requests_success(self, client, mock_partner_service):
        """Returns 200 with pending requests."""
        mock_partner_service.list_requests.return_value = PartnerRequestsResponse(
            requests=[],
        )

        response = client.get(f"{PREFIX}/requests")

        assert response.status_code == 200
        data = response.json()
        assert data["requests"] == []
        mock_partner_service.list_requests.assert_called_once_with("test-user-uuid")

    @pytest.mark.unit
    def test_list_requests_with_incoming(self, client, mock_partner_service):
        """Returns incoming and outgoing requests."""
        request_data = {
            "partnership_id": "req-001",
            "user_id": "other-user",
            "username": "alice",
            "display_name": "Alice",
            "avatar_config": {},
            "pixel_avatar_id": None,
            "direction": "incoming",
            "created_at": "2025-01-01T00:00:00Z",
        }
        mock_partner_service.list_requests.return_value = PartnerRequestsResponse(
            requests=[request_data],
        )

        response = client.get(f"{PREFIX}/requests")

        assert response.status_code == 200
        data = response.json()
        assert len(data["requests"]) == 1
        assert data["requests"][0]["direction"] == "incoming"


# =============================================================================
# GET /search - search_users
# =============================================================================


class TestSearchUsers:
    """Tests for GET /api/v1/partners/search?q=..."""

    @pytest.mark.unit
    def test_search_users_success(self, client, mock_partner_service):
        """Returns 200 with search results."""
        mock_partner_service.search_users.return_value = UserSearchResponse(
            users=[],
        )

        response = client.get(f"{PREFIX}/search", params={"q": "test"})

        assert response.status_code == 200
        data = response.json()
        assert data["users"] == []
        mock_partner_service.search_users.assert_called_once_with("test", "test-user-uuid")

    @pytest.mark.unit
    def test_search_users_with_results(self, client, mock_partner_service):
        """Returns matching users with partnership status."""
        user_result = {
            "user_id": "found-user",
            "username": "testuser",
            "display_name": "Test User",
            "avatar_config": {},
            "pixel_avatar_id": None,
            "study_interests": [],
            "partnership_status": None,
        }
        mock_partner_service.search_users.return_value = UserSearchResponse(
            users=[user_result],
        )

        response = client.get(f"{PREFIX}/search", params={"q": "test"})

        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) == 1
        assert data["users"][0]["username"] == "testuser"

    @pytest.mark.unit
    def test_search_users_missing_query_returns_422(self, client, mock_partner_service):
        """Returns 422 when query parameter is missing."""
        response = client.get(f"{PREFIX}/search")

        assert response.status_code == 422


# =============================================================================
# POST /request - send_request
# =============================================================================


class TestSendRequest:
    """Tests for POST /api/v1/partners/request."""

    @pytest.mark.unit
    def test_send_request_success(self, client, mock_partner_service):
        """Returns 200 with partnership request details."""
        mock_partner_service.send_request.return_value = PartnerRequestResponse(
            partnership_id="new-partnership-id",
            status="pending",
            message="Partner request sent",
        )

        response = client.post(
            f"{PREFIX}/request",
            json={"addressee_id": "target-user-uuid"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["partnership_id"] == "new-partnership-id"
        assert data["status"] == "pending"
        mock_partner_service.send_request.assert_called_once_with(
            "test-user-uuid", "target-user-uuid"
        )

    @pytest.mark.unit
    def test_send_request_self_partner_error(self, client, mock_partner_service):
        """Returns 400 when sending request to yourself."""
        from app.models.partner import SelfPartnerError

        mock_partner_service.send_request.side_effect = SelfPartnerError(
            "Cannot send partner request to yourself"
        )

        response = client.post(
            f"{PREFIX}/request",
            json={"addressee_id": "test-user-uuid"},
        )

        assert response.status_code == 400
        assert response.json()["code"] == "SELF_PARTNER"

    @pytest.mark.unit
    def test_send_request_already_partners_error(self, client, mock_partner_service):
        """Returns 409 when partnership already exists."""
        from app.models.partner import AlreadyPartnersError

        mock_partner_service.send_request.side_effect = AlreadyPartnersError("Already partners")

        response = client.post(
            f"{PREFIX}/request",
            json={"addressee_id": "existing-partner-uuid"},
        )

        assert response.status_code == 409
        assert response.json()["code"] == "ALREADY_PARTNERS"

    @pytest.mark.unit
    def test_send_request_partner_limit_error(self, client, mock_partner_service):
        """Returns 429 when partner limit is reached."""
        from app.models.partner import PartnerLimitError

        mock_partner_service.send_request.side_effect = PartnerLimitError(
            "Maximum partners reached"
        )

        response = client.post(
            f"{PREFIX}/request",
            json={"addressee_id": "another-user-uuid"},
        )

        assert response.status_code == 429
        assert response.json()["code"] == "PARTNER_LIMIT_EXCEEDED"

    @pytest.mark.unit
    def test_send_request_missing_body_returns_422(self, client, mock_partner_service):
        """Returns 422 when request body is missing."""
        response = client.post(f"{PREFIX}/request")

        assert response.status_code == 422


# =============================================================================
# POST /request/{partnership_id}/respond - respond_to_request
# =============================================================================


class TestRespondToRequest:
    """Tests for POST /api/v1/partners/request/{id}/respond."""

    @pytest.mark.unit
    def test_respond_accept(self, client, mock_partner_service):
        """Returns 200 when accepting a partner request."""
        mock_partner_service.respond_to_request.return_value = PartnerRespondResponse(
            partnership_id="partnership-001",
            status="accepted",
            message="Partnership accepted",
        )

        response = client.post(
            f"{PREFIX}/request/partnership-001/respond",
            json={"accept": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        mock_partner_service.respond_to_request.assert_called_once_with(
            "partnership-001", "test-user-uuid", True
        )

    @pytest.mark.unit
    def test_respond_decline(self, client, mock_partner_service):
        """Returns 200 when declining a partner request."""
        mock_partner_service.respond_to_request.return_value = PartnerRespondResponse(
            partnership_id="partnership-002",
            status="declined",
            message="Partnership declined",
        )

        response = client.post(
            f"{PREFIX}/request/partnership-002/respond",
            json={"accept": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "declined"
        mock_partner_service.respond_to_request.assert_called_once_with(
            "partnership-002", "test-user-uuid", False
        )

    @pytest.mark.unit
    def test_respond_partnership_not_found(self, client, mock_partner_service):
        """Returns 404 when partnership is not found."""
        from app.models.partner import PartnershipNotFoundError

        mock_partner_service.respond_to_request.side_effect = PartnershipNotFoundError(
            "Partnership not found"
        )

        response = client.post(
            f"{PREFIX}/request/nonexistent/respond",
            json={"accept": True},
        )

        assert response.status_code == 404
        assert response.json()["code"] == "PARTNERSHIP_NOT_FOUND"


# =============================================================================
# DELETE /{partnership_id} - remove_partner
# =============================================================================


class TestRemovePartner:
    """Tests for DELETE /api/v1/partners/{id}."""

    @pytest.mark.unit
    def test_remove_partner_success(self, client, mock_partner_service):
        """Returns 200 when successfully removing a partner."""
        mock_partner_service.remove_partner.return_value = PartnerRemoveResponse(
            message="Partner removed",
        )

        response = client.delete(f"{PREFIX}/partnership-001")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Partner removed"
        mock_partner_service.remove_partner.assert_called_once_with(
            "partnership-001", "test-user-uuid"
        )

    @pytest.mark.unit
    def test_remove_partner_not_found(self, client, mock_partner_service):
        """Returns 404 when partnership is not found."""
        from app.models.partner import PartnershipNotFoundError

        mock_partner_service.remove_partner.side_effect = PartnershipNotFoundError(
            "Partnership not found"
        )

        response = client.delete(f"{PREFIX}/nonexistent")

        assert response.status_code == 404
        assert response.json()["code"] == "PARTNERSHIP_NOT_FOUND"


# =============================================================================
# Authentication
# =============================================================================


class TestPartnersAuth:
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
    def test_list_partners_requires_auth(self, unauthenticated_client):
        """GET / returns 401 without authentication."""
        response = unauthenticated_client.get(f"{PREFIX}/")
        assert response.status_code == 401

    @pytest.mark.unit
    def test_list_requests_requires_auth(self, unauthenticated_client):
        """GET /requests returns 401 without authentication."""
        response = unauthenticated_client.get(f"{PREFIX}/requests")
        assert response.status_code == 401

    @pytest.mark.unit
    def test_search_requires_auth(self, unauthenticated_client):
        """GET /search returns 401 without authentication."""
        response = unauthenticated_client.get(f"{PREFIX}/search", params={"q": "test"})
        assert response.status_code == 401

    @pytest.mark.unit
    def test_send_request_requires_auth(self, unauthenticated_client):
        """POST /request returns 401 without authentication."""
        response = unauthenticated_client.post(
            f"{PREFIX}/request",
            json={"addressee_id": "some-user"},
        )
        assert response.status_code == 401

    @pytest.mark.unit
    def test_respond_requires_auth(self, unauthenticated_client):
        """POST /request/{id}/respond returns 401 without authentication."""
        response = unauthenticated_client.post(
            f"{PREFIX}/request/some-id/respond",
            json={"accept": True},
        )
        assert response.status_code == 401

    @pytest.mark.unit
    def test_remove_requires_auth(self, unauthenticated_client):
        """DELETE /{id} returns 401 without authentication."""
        response = unauthenticated_client.delete(f"{PREFIX}/some-id")
        assert response.status_code == 401
