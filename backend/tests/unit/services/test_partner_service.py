"""Unit tests for PartnerService.

Tests:
- send_request() - happy path, self-partner, already partners, pending exists, limit
- respond_to_request() - accept, decline, not found, wrong user
- list_partners() - returns partner info with user data joined
- list_requests() - categorizes incoming vs outgoing correctly
- remove_partner() - deletes partnership and cascades to schedules
- set_interest_tags() - valid tags, invalid tags, too many tags
- get_partnership_status() - accepted, none
"""

from unittest.mock import MagicMock

import pytest

from app.core.constants import INTEREST_TAGS, MAX_INTEREST_TAGS_PER_USER, MAX_PARTNERS
from app.models.partner import (
    AlreadyPartnersError,
    InvalidInterestTagError,
    PartnerLimitError,
    PartnerRequestExistsError,
    PartnershipNotFoundError,
    SelfPartnerError,
)
from app.services.partner_service import PartnerService

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_supabase():
    """Mock Supabase client with table-specific routing."""
    mock = MagicMock()

    partnerships_mock = MagicMock()
    users_mock = MagicMock()
    recurring_schedules_mock = MagicMock()

    def table_router(name):
        routes = {
            "partnerships": partnerships_mock,
            "users": users_mock,
            "recurring_schedules": recurring_schedules_mock,
        }
        return routes.get(name, MagicMock())

    mock.table.side_effect = table_router
    return mock, partnerships_mock, users_mock, recurring_schedules_mock


@pytest.fixture
def partner_service(mock_supabase):
    """PartnerService with mocked Supabase."""
    mock, _, _, _ = mock_supabase
    return PartnerService(supabase=mock)


# =============================================================================
# Helpers
# =============================================================================


def _make_partnership_row(
    partnership_id: str = "pship-1",
    requester_id: str = "user-a",
    addressee_id: str = "user-b",
    status: str = "pending",
    last_session_together: str = None,
) -> dict:
    """Create a partnership record dict as returned from DB."""
    return {
        "id": partnership_id,
        "requester_id": requester_id,
        "addressee_id": addressee_id,
        "status": status,
        "last_session_together": last_session_together,
    }


def _make_user_row(
    user_id: str = "user-b",
    username: str = "testuser",
    display_name: str = "Test User",
    reliability_score: float = 95.0,
    study_interests: list = None,
) -> dict:
    """Create a user record dict for partner/request lookups."""
    return {
        "id": user_id,
        "username": username,
        "display_name": display_name,
        "avatar_config": {"color": "blue"},
        "pixel_avatar_id": "char-1",
        "reliability_score": reliability_score,
        "study_interests": study_interests or [],
    }


def _setup_find_partnership(partnerships_mock, result_data):
    """Mock the _find_partnership query chain.

    Chain: .select(...).or_(...).in_(...).execute()
    """
    (
        partnerships_mock.select.return_value.or_.return_value.in_.return_value.execute.return_value
    ).data = result_data


def _setup_count_accepted(partnerships_mock, count_value):
    """Mock the _count_accepted_partners query chain.

    Chain: .select("id", count="exact").or_(...).eq(...).execute()
    """
    (
        partnerships_mock.select.return_value.or_.return_value.eq.return_value.execute.return_value
    ).count = count_value


def _setup_get_partnership(partnerships_mock, result_data):
    """Mock the _get_partnership query chain.

    Chain: .select("*").eq("id", ...).execute()
    """
    (partnerships_mock.select.return_value.eq.return_value.execute.return_value).data = result_data


# =============================================================================
# TestSendRequest
# =============================================================================


class TestSendRequest:
    """Tests for send_request()."""

    @pytest.mark.unit
    def test_send_request_success(self, partner_service, mock_supabase) -> None:
        """Happy path: no existing partnership, under limit, creates pending request."""
        _, partnerships_mock, _, _ = mock_supabase

        _setup_find_partnership(partnerships_mock, [])
        _setup_count_accepted(partnerships_mock, 3)

        created_row = _make_partnership_row(status="pending")
        partnerships_mock.insert.return_value.execute.return_value.data = [created_row]

        result = partner_service.send_request("user-a", "user-b")

        assert result["id"] == "pship-1"
        assert result["status"] == "pending"
        partnerships_mock.insert.assert_called_once_with(
            {
                "requester_id": "user-a",
                "addressee_id": "user-b",
                "status": "pending",
            }
        )

    @pytest.mark.unit
    def test_send_request_self_partner_error(self, partner_service) -> None:
        """Cannot send a partner request to yourself."""
        with pytest.raises(SelfPartnerError, match="Cannot send a partner request to yourself"):
            partner_service.send_request("user-a", "user-a")

    @pytest.mark.unit
    def test_send_request_already_partners(self, partner_service, mock_supabase) -> None:
        """Raises AlreadyPartnersError if accepted partnership exists."""
        _, partnerships_mock, _, _ = mock_supabase

        existing = _make_partnership_row(status="accepted")
        _setup_find_partnership(partnerships_mock, [existing])

        with pytest.raises(AlreadyPartnersError, match="already partners"):
            partner_service.send_request("user-a", "user-b")

    @pytest.mark.unit
    def test_send_request_pending_exists(self, partner_service, mock_supabase) -> None:
        """Raises PartnerRequestExistsError if pending request already exists."""
        _, partnerships_mock, _, _ = mock_supabase

        existing = _make_partnership_row(status="pending")
        _setup_find_partnership(partnerships_mock, [existing])

        with pytest.raises(PartnerRequestExistsError, match="already exists"):
            partner_service.send_request("user-a", "user-b")

    @pytest.mark.unit
    def test_send_request_partner_limit(self, partner_service, mock_supabase) -> None:
        """Raises PartnerLimitError when at MAX_PARTNERS accepted partners."""
        _, partnerships_mock, _, _ = mock_supabase

        _setup_find_partnership(partnerships_mock, [])
        _setup_count_accepted(partnerships_mock, MAX_PARTNERS)

        with pytest.raises(PartnerLimitError, match=f"maximum of {MAX_PARTNERS}"):
            partner_service.send_request("user-a", "user-b")


# =============================================================================
# TestRespondToRequest
# =============================================================================


class TestRespondToRequest:
    """Tests for respond_to_request()."""

    @pytest.mark.unit
    def test_respond_accept_success(self, partner_service, mock_supabase) -> None:
        """Accept a pending request: status -> accepted, accepted_at set."""
        _, partnerships_mock, _, _ = mock_supabase

        pending_row = _make_partnership_row(
            partnership_id="pship-1",
            requester_id="user-a",
            addressee_id="user-b",
            status="pending",
        )
        _setup_get_partnership(partnerships_mock, [pending_row])

        accepted_row = {**pending_row, "status": "accepted"}
        (partnerships_mock.update.return_value.eq.return_value.execute.return_value).data = [
            accepted_row
        ]

        result = partner_service.respond_to_request("pship-1", "user-b", accept=True)

        assert result["status"] == "accepted"
        update_call = partnerships_mock.update.call_args[0][0]
        assert update_call["status"] == "accepted"
        assert "accepted_at" in update_call

    @pytest.mark.unit
    def test_respond_decline_success(self, partner_service, mock_supabase) -> None:
        """Decline a pending request: status -> declined."""
        _, partnerships_mock, _, _ = mock_supabase

        pending_row = _make_partnership_row(
            partnership_id="pship-1",
            requester_id="user-a",
            addressee_id="user-b",
            status="pending",
        )
        _setup_get_partnership(partnerships_mock, [pending_row])

        declined_row = {**pending_row, "status": "declined"}
        (partnerships_mock.update.return_value.eq.return_value.execute.return_value).data = [
            declined_row
        ]

        result = partner_service.respond_to_request("pship-1", "user-b", accept=False)

        assert result["status"] == "declined"
        partnerships_mock.update.assert_called_once_with({"status": "declined"})

    @pytest.mark.unit
    def test_respond_not_found(self, partner_service, mock_supabase) -> None:
        """Raises PartnershipNotFoundError for invalid partnership_id."""
        _, partnerships_mock, _, _ = mock_supabase

        _setup_get_partnership(partnerships_mock, [])

        with pytest.raises(PartnershipNotFoundError, match="not found"):
            partner_service.respond_to_request("bad-id", "user-b", accept=True)

    @pytest.mark.unit
    def test_respond_wrong_user(self, partner_service, mock_supabase) -> None:
        """Raises PartnershipNotFoundError when user is not the addressee."""
        _, partnerships_mock, _, _ = mock_supabase

        pending_row = _make_partnership_row(
            partnership_id="pship-1",
            requester_id="user-a",
            addressee_id="user-b",
            status="pending",
        )
        _setup_get_partnership(partnerships_mock, [pending_row])

        with pytest.raises(PartnershipNotFoundError, match="addressee"):
            partner_service.respond_to_request("pship-1", "user-a", accept=True)


# =============================================================================
# TestListPartners
# =============================================================================


class TestListPartners:
    """Tests for list_partners()."""

    @pytest.mark.unit
    def test_list_partners_returns_partner_info(self, partner_service, mock_supabase) -> None:
        """Returns correct fields with user data joined from both tables."""
        _, partnerships_mock, users_mock, _ = mock_supabase

        partnership_rows = [
            _make_partnership_row(
                partnership_id="pship-1",
                requester_id="me",
                addressee_id="partner-1",
                status="accepted",
                last_session_together="2026-02-10T10:00:00Z",
            ),
            _make_partnership_row(
                partnership_id="pship-2",
                requester_id="partner-2",
                addressee_id="me",
                status="accepted",
            ),
        ]

        (
            partnerships_mock.select.return_value.or_.return_value.eq.return_value.execute.return_value
        ).data = partnership_rows

        user_rows = [
            _make_user_row(user_id="partner-1", username="alice", display_name="Alice"),
            _make_user_row(user_id="partner-2", username="bob", display_name="Bob"),
        ]

        (users_mock.select.return_value.in_.return_value.execute.return_value).data = user_rows

        result = partner_service.list_partners("me")

        assert len(result) == 2

        alice = next(p for p in result if p["user_id"] == "partner-1")
        assert alice["partnership_id"] == "pship-1"
        assert alice["username"] == "alice"
        assert alice["display_name"] == "Alice"
        assert alice["reliability_score"] == 95.0
        assert alice["last_session_together"] == "2026-02-10T10:00:00Z"

        bob = next(p for p in result if p["user_id"] == "partner-2")
        assert bob["partnership_id"] == "pship-2"
        assert bob["username"] == "bob"
        assert bob["last_session_together"] is None

    @pytest.mark.unit
    def test_list_partners_empty(self, partner_service, mock_supabase) -> None:
        """Returns empty list when user has no accepted partners."""
        _, partnerships_mock, _, _ = mock_supabase

        (
            partnerships_mock.select.return_value.or_.return_value.eq.return_value.execute.return_value
        ).data = []

        result = partner_service.list_partners("me")

        assert result == []


# =============================================================================
# TestListRequests
# =============================================================================


class TestListRequests:
    """Tests for list_requests()."""

    @pytest.mark.unit
    def test_list_requests_categorizes_direction(self, partner_service, mock_supabase) -> None:
        """Tags requests as 'incoming' when user is addressee, 'outgoing' when requester."""
        _, partnerships_mock, users_mock, _ = mock_supabase

        request_rows = [
            {
                "id": "req-1",
                "requester_id": "other-user",
                "addressee_id": "me",
                "created_at": "2026-02-10T10:00:00Z",
            },
            {
                "id": "req-2",
                "requester_id": "me",
                "addressee_id": "another-user",
                "created_at": "2026-02-11T10:00:00Z",
            },
        ]

        (
            partnerships_mock.select.return_value.or_.return_value.eq.return_value.execute.return_value
        ).data = request_rows

        user_rows = [
            _make_user_row(user_id="other-user", username="sender"),
            _make_user_row(user_id="another-user", username="receiver"),
        ]

        (users_mock.select.return_value.in_.return_value.execute.return_value).data = user_rows

        result = partner_service.list_requests("me")

        assert len(result) == 2

        incoming = next(r for r in result if r["user_id"] == "other-user")
        assert incoming["direction"] == "incoming"
        assert incoming["partnership_id"] == "req-1"

        outgoing = next(r for r in result if r["user_id"] == "another-user")
        assert outgoing["direction"] == "outgoing"
        assert outgoing["partnership_id"] == "req-2"

    @pytest.mark.unit
    def test_list_requests_empty(self, partner_service, mock_supabase) -> None:
        """Returns empty list when no pending requests exist."""
        _, partnerships_mock, _, _ = mock_supabase

        (
            partnerships_mock.select.return_value.or_.return_value.eq.return_value.execute.return_value
        ).data = []

        result = partner_service.list_requests("me")

        assert result == []


# =============================================================================
# TestRemovePartner
# =============================================================================


class TestRemovePartner:
    """Tests for remove_partner()."""

    @pytest.mark.unit
    def test_remove_partner_success(self, partner_service, mock_supabase) -> None:
        """Deletes partnership and cascades to recurring schedules."""
        _, partnerships_mock, _, recurring_mock = mock_supabase

        partnership_row = _make_partnership_row(
            partnership_id="pship-1",
            requester_id="user-a",
            addressee_id="user-b",
            status="accepted",
        )
        _setup_get_partnership(partnerships_mock, [partnership_row])

        partnerships_mock.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        schedule_with_partner = {
            "id": "sched-1",
            "partner_ids": ["user-b", "user-c"],
        }
        empty_schedule = {
            "id": "sched-2",
            "partner_ids": ["user-a"],
        }

        call_count = [0]

        def schedule_select_side_effect(*args, **kwargs):
            mock_chain = MagicMock()

            def eq_side_effect_creator(creator_id):
                def eq_active(*args, **kwargs):
                    result_mock = MagicMock()
                    if creator_id == "user-a":
                        result_mock.execute.return_value.data = [schedule_with_partner]
                    else:
                        result_mock.execute.return_value.data = [empty_schedule]
                    return result_mock

                return eq_active

            def first_eq(*args, **kwargs):
                nonlocal call_count
                call_count[0] += 1
                inner_mock = MagicMock()
                if call_count[0] <= 1:
                    inner_mock.execute.return_value.data = [schedule_with_partner]
                else:
                    inner_mock.execute.return_value.data = [empty_schedule]
                return inner_mock

            mock_chain.eq.return_value.eq.return_value = MagicMock()
            mock_chain.eq.return_value.eq.return_value.execute.return_value.data = []
            return mock_chain

        (
            recurring_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value
        ).data = []

        partner_service.remove_partner("pship-1", "user-a")

        partnerships_mock.delete.return_value.eq.assert_called_with("id", "pship-1")

    @pytest.mark.unit
    def test_remove_partner_not_found(self, partner_service, mock_supabase) -> None:
        """Raises PartnershipNotFoundError when partnership doesn't exist."""
        _, partnerships_mock, _, _ = mock_supabase

        _setup_get_partnership(partnerships_mock, [])

        with pytest.raises(PartnershipNotFoundError, match="not found"):
            partner_service.remove_partner("bad-id", "user-a")

    @pytest.mark.unit
    def test_remove_partner_not_member(self, partner_service, mock_supabase) -> None:
        """Raises PartnershipNotFoundError when user is not part of the partnership."""
        _, partnerships_mock, _, _ = mock_supabase

        partnership_row = _make_partnership_row(
            partnership_id="pship-1",
            requester_id="user-a",
            addressee_id="user-b",
            status="accepted",
        )
        _setup_get_partnership(partnerships_mock, [partnership_row])

        with pytest.raises(PartnershipNotFoundError, match="not part"):
            partner_service.remove_partner("pship-1", "user-c")

    @pytest.mark.unit
    def test_remove_partner_cascades_deactivates_empty_schedule(
        self, partner_service, mock_supabase
    ) -> None:
        """When removing partner leaves a schedule with no partners, deactivate it."""
        _, partnerships_mock, _, recurring_mock = mock_supabase

        partnership_row = _make_partnership_row(
            partnership_id="pship-1",
            requester_id="user-a",
            addressee_id="user-b",
            status="accepted",
        )
        _setup_get_partnership(partnerships_mock, [partnership_row])

        partnerships_mock.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        schedule_only_partner = {
            "id": "sched-1",
            "partner_ids": ["user-b"],
        }

        (
            recurring_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value
        ).data = [schedule_only_partner]

        recurring_mock.update.return_value.eq.return_value.execute.return_value = MagicMock()

        partner_service.remove_partner("pship-1", "user-a")

        recurring_mock.update.assert_any_call({"partner_ids": [], "is_active": False})


# =============================================================================
# TestSetInterestTags
# =============================================================================


class TestSetInterestTags:
    """Tests for set_interest_tags()."""

    @pytest.mark.unit
    def test_set_interest_tags_valid(self, partner_service, mock_supabase) -> None:
        """Updates study_interests column with valid tags."""
        _, _, users_mock, _ = mock_supabase

        users_mock.update.return_value.eq.return_value.execute.return_value = MagicMock()

        valid_tags = ["coding", "writing", "design"]
        result = partner_service.set_interest_tags("user-1", valid_tags)

        assert result == valid_tags
        users_mock.update.assert_called_once_with({"study_interests": valid_tags})

    @pytest.mark.unit
    def test_set_interest_tags_invalid(self, partner_service) -> None:
        """Raises InvalidInterestTagError for unknown tags."""
        with pytest.raises(InvalidInterestTagError, match="Invalid interest tags"):
            partner_service.set_interest_tags("user-1", ["coding", "not_a_real_tag"])

    @pytest.mark.unit
    def test_set_interest_tags_exceeds_limit(self, partner_service) -> None:
        """Raises InvalidInterestTagError when too many tags are provided."""
        too_many = INTEREST_TAGS[: MAX_INTEREST_TAGS_PER_USER + 1]
        with pytest.raises(InvalidInterestTagError, match=f"Maximum {MAX_INTEREST_TAGS_PER_USER}"):
            partner_service.set_interest_tags("user-1", too_many)

    @pytest.mark.unit
    def test_set_interest_tags_empty_is_valid(self, partner_service, mock_supabase) -> None:
        """Passing an empty list clears the user's tags."""
        _, _, users_mock, _ = mock_supabase

        users_mock.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = partner_service.set_interest_tags("user-1", [])

        assert result == []
        users_mock.update.assert_called_once_with({"study_interests": []})


# =============================================================================
# TestGetPartnershipStatus
# =============================================================================


class TestGetPartnershipStatus:
    """Tests for get_partnership_status()."""

    @pytest.mark.unit
    def test_get_partnership_status_accepted(self, partner_service, mock_supabase) -> None:
        """Returns 'accepted' when users have an accepted partnership."""
        _, partnerships_mock, _, _ = mock_supabase

        existing = _make_partnership_row(status="accepted")
        _setup_find_partnership(partnerships_mock, [existing])

        result = partner_service.get_partnership_status("user-a", "user-b")

        assert result == "accepted"

    @pytest.mark.unit
    def test_get_partnership_status_pending(self, partner_service, mock_supabase) -> None:
        """Returns 'pending' when a pending request exists."""
        _, partnerships_mock, _, _ = mock_supabase

        existing = _make_partnership_row(status="pending")
        _setup_find_partnership(partnerships_mock, [existing])

        result = partner_service.get_partnership_status("user-a", "user-b")

        assert result == "pending"

    @pytest.mark.unit
    def test_get_partnership_status_none(self, partner_service, mock_supabase) -> None:
        """Returns None when no partnership exists between users."""
        _, partnerships_mock, _, _ = mock_supabase

        _setup_find_partnership(partnerships_mock, [])

        result = partner_service.get_partnership_status("user-a", "user-b")

        assert result is None

    @pytest.mark.unit
    def test_get_partnership_status_declined_returns_none(
        self, partner_service, mock_supabase
    ) -> None:
        """Returns None when only a declined partnership exists.

        Note: _find_partnership filters by in_("status", ["pending", "accepted"]),
        so declined partnerships won't be returned from the DB. But if one did
        slip through, get_partnership_status would still return None.
        """
        _, partnerships_mock, _, _ = mock_supabase

        existing = _make_partnership_row(status="declined")
        _setup_find_partnership(partnerships_mock, [existing])

        result = partner_service.get_partnership_status("user-a", "user-b")

        assert result is None


# =============================================================================
# TestPartnerCache
# =============================================================================


class TestPartnerCache:
    """Tests for Redis partner cache."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        from unittest.mock import AsyncMock

        redis = MagicMock()
        redis.smembers = AsyncMock(return_value=set())
        redis.sadd = AsyncMock()
        redis.expire = AsyncMock()
        redis.delete = AsyncMock()
        redis.set = AsyncMock(return_value=True)  # Lock acquired
        return redis

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_accepted_partner_ids_cache_miss(
        self, partner_service: PartnerService, mock_supabase, mock_redis
    ):
        """On cache miss, should query DB and cache result."""
        _, partnerships_mock, _, _ = mock_supabase
        partner_service._redis = mock_redis
        mock_redis.smembers.return_value = set()  # Cache miss

        # Mock DB response
        (
            partnerships_mock.select.return_value.or_.return_value.eq.return_value.execute.return_value
        ) = MagicMock(
            data=[
                {"requester_id": "user-1", "addressee_id": "partner-1"},
                {"requester_id": "partner-2", "addressee_id": "user-1"},
            ]
        )

        result = await partner_service.get_accepted_partner_ids("user-1")

        assert result == {"partner-1", "partner-2"}
        mock_redis.sadd.assert_called_once()
        mock_redis.expire.assert_called_once_with("partners:user-1:accepted", 300)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_accepted_partner_ids_cache_hit(
        self, partner_service: PartnerService, mock_supabase, mock_redis
    ):
        """On cache hit, should return cached data without DB query."""
        _, partnerships_mock, _, _ = mock_supabase
        partner_service._redis = mock_redis
        mock_redis.smembers.return_value = {"partner-1", "partner-2"}  # Cache hit

        result = await partner_service.get_accepted_partner_ids("user-1")

        assert result == {"partner-1", "partner-2"}
        # DB should NOT be called
        partnerships_mock.select.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_invalidate_partner_cache(self, partner_service: PartnerService, mock_redis):
        """Should delete cache key for user."""
        partner_service._redis = mock_redis

        await partner_service._invalidate_partner_cache("user-1")

        mock_redis.delete.assert_called_once_with("partners:user-1:accepted")
