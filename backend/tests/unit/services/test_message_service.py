"""Unit tests for MessageService.

Tests:
- create_direct_conversation() - happy path, not partners, already exists, limit, enriched
- create_group_conversation() - happy path, not partners, too many, too few, limit
- send_message() - happy path, not member, read-only, not found
- get_messages() - returns with sender, cursor pagination, soft-deleted content
- list_conversations() - returns with unread + last message, empty list
- mark_read() - happy path, not member
- toggle_reaction() - add, remove, invalid emoji, not member
- delete_message() - happy path, not owner
- add_group_member() - happy path, not group, group full
- leave_group() - happy path, dissolves when below min
- get_conversation() - happy path, not found
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.constants import (
    MAX_DIRECT_CONVERSATIONS,
    MAX_GROUP_CONVERSATIONS,
    MAX_GROUP_SIZE,
    MIN_GROUP_SIZE,
)
from app.models.message import (
    ConversationLimitError,
    ConversationNotFoundError,
    ConversationReadOnlyError,
    DirectConversationExistsError,
    GroupSizeError,
    InvalidReactionError,
    MessageNotFoundError,
    NotConversationMemberError,
    NotMessageOwnerError,
    NotMutualPartnersError,
)
from app.services.message_service import MessageService

# =============================================================================
# Fixtures
# =============================================================================

USER_A = "user-a"
USER_B = "user-b"
USER_C = "user-c"
USER_D = "user-d"
CONV_ID = "conv-1"
MSG_ID = "msg-1"


@pytest.fixture
def mock_supabase():
    """Mock Supabase client with table-specific routing."""
    mock = MagicMock()

    conversations_mock = MagicMock()
    conversation_members_mock = MagicMock()
    messages_mock = MagicMock()
    users_mock = MagicMock()
    partnerships_mock = MagicMock()

    def table_router(name):
        routes = {
            "conversations": conversations_mock,
            "conversation_members": conversation_members_mock,
            "messages": messages_mock,
            "users": users_mock,
            "partnerships": partnerships_mock,
        }
        return routes.get(name, MagicMock())

    mock.table.side_effect = table_router
    return (
        mock,
        conversations_mock,
        conversation_members_mock,
        messages_mock,
        users_mock,
        partnerships_mock,
    )


@pytest.fixture
def service(mock_supabase):
    """MessageService with mocked Supabase."""
    mock, _, _, _, _, _ = mock_supabase
    return MessageService(supabase=mock)


# =============================================================================
# Helpers
# =============================================================================


def _make_conversation(
    conv_id: str = CONV_ID,
    conv_type: str = "direct",
    name: str = None,
    created_by: str = USER_A,
    updated_at: str = "2026-02-12T10:00:00Z",
) -> dict:
    return {
        "id": conv_id,
        "type": conv_type,
        "name": name,
        "created_by": created_by,
        "updated_at": updated_at,
    }


def _make_member_row(
    conversation_id: str = CONV_ID,
    user_id: str = USER_A,
    last_read_at: str = None,
) -> dict:
    return {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "last_read_at": last_read_at,
    }


def _make_message(
    msg_id: str = MSG_ID,
    conversation_id: str = CONV_ID,
    sender_id: str = USER_A,
    content: str = "Hello",
    reactions: dict = None,
    deleted_at: str = None,
    created_at: str = "2026-02-12T10:00:00Z",
) -> dict:
    return {
        "id": msg_id,
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "content": content,
        "reactions": reactions or {},
        "deleted_at": deleted_at,
        "created_at": created_at,
    }


def _make_user_row(
    user_id: str = USER_B,
    username: str = "testuser",
    display_name: str = "Test User",
) -> dict:
    return {
        "id": user_id,
        "username": username,
        "display_name": display_name,
        "avatar_config": {"color": "blue"},
        "pixel_avatar_id": "char-1",
    }


def _make_partnership_row(
    partnership_id: str = "pship-1",
    requester_id: str = USER_A,
    addressee_id: str = USER_B,
    status: str = "accepted",
) -> dict:
    return {
        "id": partnership_id,
        "requester_id": requester_id,
        "addressee_id": addressee_id,
        "status": status,
    }


# -- Mock chain helpers --


def _setup_partnership_found(partnerships_mock, data):
    """Mock _validate_partnership chain: .select(...).or_(...).eq(...).execute()"""
    chain = partnerships_mock.select.return_value
    chain.or_.return_value.eq.return_value.execute.return_value = MagicMock(data=data)


def _setup_get_conversation(conversations_mock, data):
    """Mock _get_conversation chain: .select("*").eq("id", ...).execute()"""
    chain = conversations_mock.select.return_value
    chain.eq.return_value.execute.return_value = MagicMock(data=data)


def _setup_verify_membership(members_mock, data):
    """Mock _verify_membership chain: .select("user_id").eq(...).eq(...).execute()"""
    chain = members_mock.select.return_value
    chain.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=data)


def _setup_get_message(messages_mock, data):
    """Mock _get_message chain: .select("*").eq("id", ...).execute()"""
    chain = messages_mock.select.return_value
    chain.eq.return_value.execute.return_value = MagicMock(data=data)


def _setup_users_lookup(users_mock, data):
    """Mock _get_user_profiles chain: .select(...).in_("id", ...).execute()"""
    chain = users_mock.select.return_value
    chain.in_.return_value.execute.return_value = MagicMock(data=data)


def _setup_find_direct_none(members_mock):
    """Mock _find_direct_conversation returning None (first query returns empty)."""
    chain = members_mock.select.return_value
    chain.eq.return_value.execute.return_value = MagicMock(data=[])


def _setup_count_conversations(members_mock, conversations_mock, member_data, count):
    """Mock _count_conversations: members query + conversations count query."""
    m_chain = members_mock.select.return_value
    m_chain.eq.return_value.execute.return_value = MagicMock(data=member_data)

    c_chain = conversations_mock.select.return_value
    c_chain.in_.return_value.eq.return_value.execute.return_value = MagicMock(count=count)


# =============================================================================
# TestCreateDirectConversation
# =============================================================================


class TestCreateDirectConversation:
    """Tests for create_direct_conversation().

    Note: create_direct_conversation calls multiple private helpers that all
    query the conversation_members table (_find_direct_conversation,
    _count_conversations, _enrich_conversation). Since the same mock chain
    can only return one value, we mock the private helpers for the happy-path
    and limit tests, and test the sub-calls via other test classes.
    """

    @pytest.mark.unit
    def test_happy_path_creates_conversation_and_members(self, service, mock_supabase) -> None:
        """Creates a direct conversation with 2 members and returns enriched data."""
        (
            _,
            conversations_mock,
            members_mock,
            messages_mock,
            users_mock,
            partnerships_mock,
        ) = mock_supabase

        enriched = {
            "id": CONV_ID,
            "type": "direct",
            "name": None,
            "members": [],
            "last_message": None,
            "unread_count": 0,
            "is_read_only": False,
            "updated_at": "2026-02-12T10:00:00Z",
        }

        with (
            patch.object(service, "_validate_partnership"),
            patch.object(service, "_find_direct_conversation", return_value=None),
            patch.object(service, "_count_conversations", return_value=0),
            patch.object(service, "_enrich_conversation", return_value=enriched),
        ):
            conv = _make_conversation()
            conversations_mock.insert.return_value.execute.return_value = MagicMock(data=[conv])
            members_mock.insert.return_value.execute.return_value = MagicMock(data=[])

            result = service.create_direct_conversation(USER_A, USER_B)

            assert result["id"] == CONV_ID
            assert result["type"] == "direct"
            conversations_mock.insert.assert_called_once()
            insert_arg = conversations_mock.insert.call_args[0][0]
            assert insert_arg["type"] == "direct"
            assert insert_arg["created_by"] == USER_A
            members_mock.insert.assert_called_once()
            member_insert_arg = members_mock.insert.call_args[0][0]
            assert len(member_insert_arg) == 2

    @pytest.mark.unit
    def test_not_partners_raises(self, service, mock_supabase) -> None:
        """Raises NotMutualPartnersError when users are not accepted partners."""
        _, _, _, _, _, partnerships_mock = mock_supabase

        _setup_partnership_found(partnerships_mock, [])

        with pytest.raises(NotMutualPartnersError, match="mutual partners"):
            service.create_direct_conversation(USER_A, USER_B)

    @pytest.mark.unit
    def test_already_exists_raises(self, service, mock_supabase) -> None:
        """Raises DirectConversationExistsError when direct conversation exists."""
        existing_conv = _make_conversation()

        with (
            patch.object(service, "_validate_partnership"),
            patch.object(service, "_find_direct_conversation", return_value=existing_conv),
        ):
            with pytest.raises(DirectConversationExistsError, match="already exists"):
                service.create_direct_conversation(USER_A, USER_B)

    @pytest.mark.unit
    def test_limit_exceeded_raises(self, service, mock_supabase) -> None:
        """Raises ConversationLimitError when at max direct conversations."""
        with (
            patch.object(service, "_validate_partnership"),
            patch.object(service, "_find_direct_conversation", return_value=None),
            patch.object(service, "_count_conversations", return_value=MAX_DIRECT_CONVERSATIONS),
        ):
            with pytest.raises(
                ConversationLimitError,
                match=f"Maximum of {MAX_DIRECT_CONVERSATIONS}",
            ):
                service.create_direct_conversation(USER_A, USER_B)

    @pytest.mark.unit
    def test_returns_enriched_conversation(self, service, mock_supabase) -> None:
        """Returned conversation includes members, last_message, unread_count, is_read_only."""
        _, conversations_mock, members_mock, _, _, _ = mock_supabase

        enriched = {
            "id": CONV_ID,
            "type": "direct",
            "name": None,
            "members": [
                {"user_id": USER_A, "username": "alice"},
                {"user_id": USER_B, "username": "bob"},
            ],
            "last_message": None,
            "unread_count": 0,
            "is_read_only": False,
            "updated_at": "2026-02-12T10:00:00Z",
        }

        with (
            patch.object(service, "_validate_partnership"),
            patch.object(service, "_find_direct_conversation", return_value=None),
            patch.object(service, "_count_conversations", return_value=0),
            patch.object(service, "_enrich_conversation", return_value=enriched),
        ):
            conv = _make_conversation()
            conversations_mock.insert.return_value.execute.return_value = MagicMock(data=[conv])
            members_mock.insert.return_value.execute.return_value = MagicMock(data=[])

            result = service.create_direct_conversation(USER_A, USER_B)

            assert "members" in result
            assert len(result["members"]) == 2
            assert "last_message" in result
            assert "unread_count" in result
            assert "is_read_only" in result


# =============================================================================
# TestCreateGroupConversation
# =============================================================================


class TestCreateGroupConversation:
    """Tests for create_group_conversation()."""

    @pytest.mark.unit
    def test_happy_path_creates_group(self, service, mock_supabase) -> None:
        """Creates a group conversation with multiple members."""
        (
            _,
            conversations_mock,
            members_mock,
            messages_mock,
            users_mock,
            partnerships_mock,
        ) = mock_supabase

        _setup_partnership_found(partnerships_mock, [_make_partnership_row()])

        m_chain = members_mock.select.return_value
        m_chain.eq.return_value.execute.return_value = MagicMock(data=[])

        c_chain = conversations_mock.select.return_value
        c_chain.in_.return_value.eq.return_value.execute.return_value = MagicMock(count=0)

        conv = _make_conversation(conv_type="group", name="Study Buddies")
        conversations_mock.insert.return_value.execute.return_value = MagicMock(data=[conv])
        members_mock.insert.return_value.execute.return_value = MagicMock(data=[])

        member_rows = [
            _make_member_row(user_id=USER_A),
            _make_member_row(user_id=USER_B),
            _make_member_row(user_id=USER_C),
        ]
        members_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=member_rows
        )

        _setup_users_lookup(
            users_mock,
            [
                _make_user_row(user_id=USER_A, username="alice"),
                _make_user_row(user_id=USER_B, username="bob"),
                _make_user_row(user_id=USER_C, username="charlie"),
            ],
        )

        messages_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = service.create_group_conversation(USER_A, [USER_B, USER_C], "Study Buddies")

        assert result["id"] == CONV_ID
        conversations_mock.insert.assert_called_once()
        insert_arg = conversations_mock.insert.call_args[0][0]
        assert insert_arg["type"] == "group"
        assert insert_arg["name"] == "Study Buddies"

    @pytest.mark.unit
    def test_not_all_mutual_partners_raises(self, service, mock_supabase) -> None:
        """Raises NotMutualPartnersError when a member is not a partner of creator."""
        _, _, _, _, _, partnerships_mock = mock_supabase

        _setup_partnership_found(partnerships_mock, [])

        with pytest.raises(NotMutualPartnersError, match="mutual partners"):
            service.create_group_conversation(USER_A, [USER_B, USER_C], "Group")

    @pytest.mark.unit
    def test_too_many_members_raises(self, service, mock_supabase) -> None:
        """Raises GroupSizeError when group exceeds MAX_GROUP_SIZE."""
        _, _, _, _, _, _ = mock_supabase

        too_many_ids = [f"user-{i}" for i in range(MAX_GROUP_SIZE + 1)]

        with pytest.raises(GroupSizeError, match=f"cannot exceed {MAX_GROUP_SIZE}"):
            service.create_group_conversation(USER_A, too_many_ids, "Big Group")

    @pytest.mark.unit
    def test_too_few_members_raises(self, service, mock_supabase) -> None:
        """Raises GroupSizeError when group has fewer than MIN_GROUP_SIZE (including creator)."""
        _, _, _, _, _, _ = mock_supabase

        with pytest.raises(GroupSizeError, match=f"at least {MIN_GROUP_SIZE}"):
            service.create_group_conversation(USER_A, [], "Solo Group")

    @pytest.mark.unit
    def test_limit_exceeded_raises(self, service, mock_supabase) -> None:
        """Raises ConversationLimitError when at max group conversations."""
        (
            _,
            conversations_mock,
            members_mock,
            _,
            _,
            partnerships_mock,
        ) = mock_supabase

        _setup_partnership_found(partnerships_mock, [_make_partnership_row()])

        member_data = [{"conversation_id": f"conv-{i}"} for i in range(MAX_GROUP_CONVERSATIONS)]
        m_chain = members_mock.select.return_value
        m_chain.eq.return_value.execute.return_value = MagicMock(data=member_data)

        c_chain = conversations_mock.select.return_value
        c_chain.in_.return_value.eq.return_value.execute.return_value = MagicMock(
            count=MAX_GROUP_CONVERSATIONS
        )

        with pytest.raises(
            ConversationLimitError,
            match=f"Maximum of {MAX_GROUP_CONVERSATIONS}",
        ):
            service.create_group_conversation(USER_A, [USER_B], "Group")


# =============================================================================
# TestSendMessage
# =============================================================================


class TestSendMessage:
    """Tests for send_message()."""

    @pytest.mark.unit
    def test_happy_path_sends_message(self, service, mock_supabase) -> None:
        """Inserts a message, updates conversation updated_at, returns with sender."""
        (
            _,
            conversations_mock,
            members_mock,
            messages_mock,
            users_mock,
            partnerships_mock,
        ) = mock_supabase

        conv = _make_conversation(conv_type="group")
        _setup_get_conversation(conversations_mock, [conv])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])

        msg = _make_message(sender_id=USER_A, content="Hello group!")
        messages_mock.insert.return_value.execute.return_value = MagicMock(data=[msg])

        conversations_mock.update.return_value.eq.return_value.execute.return_value = MagicMock()

        _setup_users_lookup(users_mock, [_make_user_row(user_id=USER_A, username="alice")])

        result = service.send_message(CONV_ID, USER_A, "Hello group!")

        assert result["id"] == MSG_ID
        assert result["content"] == "Hello group!"
        assert result["sender"]["username"] == "alice"
        messages_mock.insert.assert_called_once()
        conversations_mock.update.assert_called_once()

    @pytest.mark.unit
    def test_not_member_raises(self, service, mock_supabase) -> None:
        """Raises NotConversationMemberError when sender is not a member."""
        _, conversations_mock, members_mock, _, _, _ = mock_supabase

        _setup_get_conversation(conversations_mock, [_make_conversation()])
        _setup_verify_membership(members_mock, [])

        with pytest.raises(NotConversationMemberError, match="not a member"):
            service.send_message(CONV_ID, USER_A, "Hello")

    @pytest.mark.unit
    def test_read_only_raises(self, service, mock_supabase) -> None:
        """Raises ConversationReadOnlyError for unpartnered direct conversations."""
        (
            _,
            conversations_mock,
            members_mock,
            _,
            _,
            partnerships_mock,
        ) = mock_supabase

        conv = _make_conversation(conv_type="direct")
        _setup_get_conversation(conversations_mock, [conv])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])

        member_rows = [
            _make_member_row(user_id=USER_A),
            _make_member_row(user_id=USER_B),
        ]
        members_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=member_rows
        )

        _setup_partnership_found(partnerships_mock, [])

        with pytest.raises(ConversationReadOnlyError, match="read-only"):
            service.send_message(CONV_ID, USER_A, "Hello")

    @pytest.mark.unit
    def test_conversation_not_found_raises(self, service, mock_supabase) -> None:
        """Raises ConversationNotFoundError when conversation doesn't exist."""
        _, conversations_mock, _, _, _, _ = mock_supabase

        _setup_get_conversation(conversations_mock, [])

        with pytest.raises(ConversationNotFoundError, match="not found"):
            service.send_message(CONV_ID, USER_A, "Hello")


# =============================================================================
# TestGetMessages
# =============================================================================


class TestGetMessages:
    """Tests for get_messages()."""

    @pytest.mark.unit
    def test_returns_messages_with_sender_info(self, service, mock_supabase) -> None:
        """Returns messages enriched with sender profile information."""
        (
            _,
            conversations_mock,
            members_mock,
            messages_mock,
            users_mock,
            _,
        ) = mock_supabase

        _setup_get_conversation(conversations_mock, [_make_conversation()])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])

        msg_rows = [
            _make_message(msg_id="msg-1", sender_id=USER_B, content="Hi"),
            _make_message(msg_id="msg-2", sender_id=USER_A, content="Hey"),
        ]
        msg_chain = messages_mock.select.return_value
        msg_chain.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=msg_rows)
        )

        _setup_users_lookup(
            users_mock,
            [
                _make_user_row(user_id=USER_A, username="alice"),
                _make_user_row(user_id=USER_B, username="bob"),
            ],
        )

        result = service.get_messages(CONV_ID, USER_A)

        assert len(result["messages"]) == 2
        assert result["has_more"] is False
        assert result["next_cursor"] is None
        assert result["messages"][0]["sender"]["username"] == "bob"

    @pytest.mark.unit
    def test_cursor_pagination(self, service, mock_supabase) -> None:
        """Returns has_more=True and next_cursor when more messages exist."""
        (
            _,
            conversations_mock,
            members_mock,
            messages_mock,
            users_mock,
            _,
        ) = mock_supabase

        _setup_get_conversation(conversations_mock, [_make_conversation()])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])

        limit = 2
        msg_rows = [
            _make_message(
                msg_id=f"msg-{i}",
                sender_id=USER_A,
                created_at=f"2026-02-12T10:0{i}:00Z",
            )
            for i in range(limit + 1)
        ]
        msg_chain = messages_mock.select.return_value
        msg_chain.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=msg_rows)
        )

        _setup_users_lookup(users_mock, [_make_user_row(user_id=USER_A, username="alice")])

        result = service.get_messages(CONV_ID, USER_A, limit=limit)

        assert result["has_more"] is True
        assert result["next_cursor"] is not None
        assert len(result["messages"]) == limit

    @pytest.mark.unit
    def test_soft_deleted_messages_have_empty_content(self, service, mock_supabase) -> None:
        """Messages with deleted_at set have their content blanked."""
        (
            _,
            conversations_mock,
            members_mock,
            messages_mock,
            users_mock,
            _,
        ) = mock_supabase

        _setup_get_conversation(conversations_mock, [_make_conversation()])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])

        msg_rows = [
            _make_message(
                msg_id="msg-deleted",
                sender_id=USER_B,
                content="secret",
                deleted_at="2026-02-12T11:00:00Z",
            ),
        ]
        msg_chain = messages_mock.select.return_value
        msg_chain.eq.return_value.order.return_value.limit.return_value.execute.return_value = (
            MagicMock(data=msg_rows)
        )

        _setup_users_lookup(users_mock, [_make_user_row(user_id=USER_B, username="bob")])

        result = service.get_messages(CONV_ID, USER_A)

        assert result["messages"][0]["content"] == ""

    @pytest.mark.unit
    def test_not_member_raises(self, service, mock_supabase) -> None:
        """Raises NotConversationMemberError when user is not a member."""
        _, conversations_mock, members_mock, _, _, _ = mock_supabase

        _setup_get_conversation(conversations_mock, [_make_conversation()])
        _setup_verify_membership(members_mock, [])

        with pytest.raises(NotConversationMemberError, match="not a member"):
            service.get_messages(CONV_ID, USER_A)


# =============================================================================
# TestListConversations
# =============================================================================


class TestListConversations:
    """Tests for list_conversations()."""

    @pytest.mark.unit
    def test_returns_conversations_with_metadata(self, service, mock_supabase) -> None:
        """Returns conversations with unread count and last message."""
        (
            _,
            conversations_mock,
            members_mock,
            messages_mock,
            users_mock,
            partnerships_mock,
        ) = mock_supabase

        members_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[_make_member_row(conversation_id=CONV_ID, user_id=USER_A)]
        )

        conv = _make_conversation(conv_type="group")
        conversations_mock.select.return_value.in_.return_value.order.return_value.execute.return_value = MagicMock(
            data=[conv]
        )

        member_rows = [
            _make_member_row(user_id=USER_A, last_read_at="2026-02-12T09:00:00Z"),
            _make_member_row(user_id=USER_B),
        ]
        members_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=member_rows
        )

        _setup_users_lookup(
            users_mock,
            [
                _make_user_row(user_id=USER_A, username="alice"),
                _make_user_row(user_id=USER_B, username="bob"),
            ],
        )

        last_msg = _make_message(sender_id=USER_B, content="Latest")
        messages_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[last_msg]
        )

        messages_mock.select.return_value.eq.return_value.gt.return_value.neq.return_value.execute.return_value = MagicMock(
            count=3
        )

        result = service.list_conversations(USER_A)

        assert len(result) == 1
        assert result[0]["id"] == CONV_ID

    @pytest.mark.unit
    def test_empty_list_when_no_conversations(self, service, mock_supabase) -> None:
        """Returns empty list when user has no conversations."""
        _, _, members_mock, _, _, _ = mock_supabase

        members_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

        result = service.list_conversations(USER_A)

        assert result == []


# =============================================================================
# TestMarkRead
# =============================================================================


class TestMarkRead:
    """Tests for mark_read()."""

    @pytest.mark.unit
    def test_happy_path_updates_last_read_at(self, service, mock_supabase) -> None:
        """Updates last_read_at for the user's membership and returns timestamp."""
        _, conversations_mock, members_mock, _, _, _ = mock_supabase

        _setup_get_conversation(conversations_mock, [_make_conversation()])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])

        members_mock.update.return_value.eq.return_value.eq.return_value.execute.return_value = (
            MagicMock()
        )

        result = service.mark_read(CONV_ID, USER_A)

        assert result["conversation_id"] == CONV_ID
        assert "last_read_at" in result
        members_mock.update.assert_called_once()

    @pytest.mark.unit
    def test_not_member_raises(self, service, mock_supabase) -> None:
        """Raises NotConversationMemberError when user is not a member."""
        _, conversations_mock, members_mock, _, _, _ = mock_supabase

        _setup_get_conversation(conversations_mock, [_make_conversation()])
        _setup_verify_membership(members_mock, [])

        with pytest.raises(NotConversationMemberError, match="not a member"):
            service.mark_read(CONV_ID, USER_A)


# =============================================================================
# TestToggleReaction
# =============================================================================


class TestToggleReaction:
    """Tests for toggle_reaction()."""

    @pytest.mark.unit
    def test_add_reaction(self, service, mock_supabase) -> None:
        """Adds user to emoji list when not yet reacted."""
        _, _, members_mock, messages_mock, _, _ = mock_supabase

        msg = _make_message(reactions={})
        _setup_get_message(messages_mock, [msg])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])

        messages_mock.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = service.toggle_reaction(MSG_ID, USER_A, "\u2764\ufe0f")

        assert result["message_id"] == MSG_ID
        assert USER_A in result["reactions"]["\u2764\ufe0f"]

    @pytest.mark.unit
    def test_remove_reaction(self, service, mock_supabase) -> None:
        """Removes user from emoji list and cleans empty key."""
        _, _, members_mock, messages_mock, _, _ = mock_supabase

        msg = _make_message(reactions={"\u2764\ufe0f": [USER_A]})
        _setup_get_message(messages_mock, [msg])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])

        messages_mock.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = service.toggle_reaction(MSG_ID, USER_A, "\u2764\ufe0f")

        assert result["message_id"] == MSG_ID
        assert "\u2764\ufe0f" not in result["reactions"]

    @pytest.mark.unit
    def test_remove_reaction_keeps_other_users(self, service, mock_supabase) -> None:
        """When removing a reaction, other users' reactions are preserved."""
        _, _, members_mock, messages_mock, _, _ = mock_supabase

        msg = _make_message(reactions={"\u2764\ufe0f": [USER_A, USER_B]})
        _setup_get_message(messages_mock, [msg])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])

        messages_mock.update.return_value.eq.return_value.execute.return_value = MagicMock()

        result = service.toggle_reaction(MSG_ID, USER_A, "\u2764\ufe0f")

        assert result["reactions"]["\u2764\ufe0f"] == [USER_B]

    @pytest.mark.unit
    def test_invalid_emoji_raises(self, service, mock_supabase) -> None:
        """Raises InvalidReactionError for emojis not in ALLOWED_REACTIONS."""
        with pytest.raises(InvalidReactionError, match="Invalid reaction"):
            service.toggle_reaction(MSG_ID, USER_A, "poop")

    @pytest.mark.unit
    def test_not_member_raises(self, service, mock_supabase) -> None:
        """Raises NotConversationMemberError when user is not in the conversation."""
        _, _, members_mock, messages_mock, _, _ = mock_supabase

        msg = _make_message()
        _setup_get_message(messages_mock, [msg])
        _setup_verify_membership(members_mock, [])

        with pytest.raises(NotConversationMemberError, match="not a member"):
            service.toggle_reaction(MSG_ID, USER_A, "\u2764\ufe0f")

    @pytest.mark.unit
    def test_message_not_found_raises(self, service, mock_supabase) -> None:
        """Raises MessageNotFoundError when the message doesn't exist."""
        _, _, _, messages_mock, _, _ = mock_supabase

        _setup_get_message(messages_mock, [])

        with pytest.raises(MessageNotFoundError, match="not found"):
            service.toggle_reaction(MSG_ID, USER_A, "\u2764\ufe0f")


# =============================================================================
# TestDeleteMessage
# =============================================================================


class TestDeleteMessage:
    """Tests for delete_message()."""

    @pytest.mark.unit
    def test_happy_path_sets_deleted_at(self, service, mock_supabase) -> None:
        """Sets deleted_at on the message (soft delete)."""
        _, _, _, messages_mock, _, _ = mock_supabase

        msg = _make_message(sender_id=USER_A)
        _setup_get_message(messages_mock, [msg])

        messages_mock.update.return_value.eq.return_value.execute.return_value = MagicMock()

        service.delete_message(MSG_ID, USER_A)

        messages_mock.update.assert_called_once()
        update_arg = messages_mock.update.call_args[0][0]
        assert "deleted_at" in update_arg

    @pytest.mark.unit
    def test_not_owner_raises(self, service, mock_supabase) -> None:
        """Raises NotMessageOwnerError when user is not the sender."""
        _, _, _, messages_mock, _, _ = mock_supabase

        msg = _make_message(sender_id=USER_B)
        _setup_get_message(messages_mock, [msg])

        with pytest.raises(NotMessageOwnerError, match="only delete your own"):
            service.delete_message(MSG_ID, USER_A)

    @pytest.mark.unit
    def test_message_not_found_raises(self, service, mock_supabase) -> None:
        """Raises MessageNotFoundError when message doesn't exist."""
        _, _, _, messages_mock, _, _ = mock_supabase

        _setup_get_message(messages_mock, [])

        with pytest.raises(MessageNotFoundError, match="not found"):
            service.delete_message(MSG_ID, USER_A)


# =============================================================================
# TestAddGroupMember
# =============================================================================


class TestAddGroupMember:
    """Tests for add_group_member()."""

    @pytest.mark.unit
    def test_happy_path_adds_member(self, service, mock_supabase) -> None:
        """Adds a new member to a group conversation."""
        (
            _,
            conversations_mock,
            members_mock,
            _,
            _,
            partnerships_mock,
        ) = mock_supabase

        conv = _make_conversation(conv_type="group")
        _setup_get_conversation(conversations_mock, [conv])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])
        _setup_partnership_found(partnerships_mock, [_make_partnership_row()])

        existing_members = [
            {"user_id": USER_A},
            {"user_id": USER_B},
        ]
        members_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=existing_members
        )

        members_mock.insert.return_value.execute.return_value = MagicMock(data=[])

        service.add_group_member(CONV_ID, USER_A, USER_C)

        members_mock.insert.assert_called_once()
        insert_arg = members_mock.insert.call_args[0][0]
        assert insert_arg["user_id"] == USER_C

    @pytest.mark.unit
    def test_not_group_raises(self, service, mock_supabase) -> None:
        """Raises ConversationNotFoundError when conversation is not a group."""
        _, conversations_mock, _, _, _, _ = mock_supabase

        conv = _make_conversation(conv_type="direct")
        _setup_get_conversation(conversations_mock, [conv])

        with pytest.raises(ConversationNotFoundError, match="group conversations"):
            service.add_group_member(CONV_ID, USER_A, USER_C)

    @pytest.mark.unit
    def test_group_full_raises(self, service, mock_supabase) -> None:
        """Raises GroupSizeError when group is at MAX_GROUP_SIZE."""
        (
            _,
            conversations_mock,
            members_mock,
            _,
            _,
            partnerships_mock,
        ) = mock_supabase

        conv = _make_conversation(conv_type="group")
        _setup_get_conversation(conversations_mock, [conv])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])
        _setup_partnership_found(partnerships_mock, [_make_partnership_row()])

        full_members = [{"user_id": f"user-{i}"} for i in range(MAX_GROUP_SIZE)]
        members_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=full_members
        )

        new_member = "new-user"
        with pytest.raises(GroupSizeError, match=f"cannot exceed {MAX_GROUP_SIZE}"):
            service.add_group_member(CONV_ID, USER_A, new_member)

    @pytest.mark.unit
    def test_already_member_is_noop(self, service, mock_supabase) -> None:
        """Adding an existing member is a no-op (no error, no insert)."""
        (
            _,
            conversations_mock,
            members_mock,
            _,
            _,
            partnerships_mock,
        ) = mock_supabase

        conv = _make_conversation(conv_type="group")
        _setup_get_conversation(conversations_mock, [conv])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])
        _setup_partnership_found(partnerships_mock, [_make_partnership_row()])

        existing_members = [
            {"user_id": USER_A},
            {"user_id": USER_B},
        ]
        members_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=existing_members
        )

        service.add_group_member(CONV_ID, USER_A, USER_B)

        members_mock.insert.assert_not_called()


# =============================================================================
# TestLeaveGroup
# =============================================================================


class TestLeaveGroup:
    """Tests for leave_group()."""

    @pytest.mark.unit
    def test_happy_path_removes_membership(self, service, mock_supabase) -> None:
        """Removes the user's membership from the group."""
        _, conversations_mock, members_mock, _, _, _ = mock_supabase

        conv = _make_conversation(conv_type="group")
        _setup_get_conversation(conversations_mock, [conv])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])

        members_mock.delete.return_value.eq.return_value.eq.return_value.execute.return_value = (
            MagicMock()
        )

        remaining_result = MagicMock()
        remaining_result.count = MIN_GROUP_SIZE
        remaining_result.data = [{"user_id": USER_B}, {"user_id": USER_C}]
        members_mock.select.return_value.eq.return_value.execute.return_value = remaining_result

        service.leave_group(CONV_ID, USER_A)

        members_mock.delete.assert_called_once()

    @pytest.mark.unit
    def test_dissolves_group_below_min_size(self, service, mock_supabase) -> None:
        """Dissolves the group when leaving drops membership below MIN_GROUP_SIZE."""
        _, conversations_mock, members_mock, _, _, _ = mock_supabase

        conv = _make_conversation(conv_type="group")
        _setup_get_conversation(conversations_mock, [conv])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])

        members_mock.delete.return_value.eq.return_value.eq.return_value.execute.return_value = (
            MagicMock()
        )

        remaining_result = MagicMock()
        remaining_result.count = MIN_GROUP_SIZE - 1
        remaining_result.data = [{"user_id": USER_B}]
        members_mock.select.return_value.eq.return_value.execute.return_value = remaining_result

        members_mock.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        service.leave_group(CONV_ID, USER_A)

        assert members_mock.delete.call_count >= 2

    @pytest.mark.unit
    def test_not_group_raises(self, service, mock_supabase) -> None:
        """Raises ConversationNotFoundError when conversation is not a group."""
        _, conversations_mock, _, _, _, _ = mock_supabase

        conv = _make_conversation(conv_type="direct")
        _setup_get_conversation(conversations_mock, [conv])

        with pytest.raises(ConversationNotFoundError, match="group conversations"):
            service.leave_group(CONV_ID, USER_A)

    @pytest.mark.unit
    def test_not_member_raises(self, service, mock_supabase) -> None:
        """Raises NotConversationMemberError when user is not a member."""
        _, conversations_mock, members_mock, _, _, _ = mock_supabase

        conv = _make_conversation(conv_type="group")
        _setup_get_conversation(conversations_mock, [conv])
        _setup_verify_membership(members_mock, [])

        with pytest.raises(NotConversationMemberError, match="not a member"):
            service.leave_group(CONV_ID, USER_A)


# =============================================================================
# TestGetConversation
# =============================================================================


class TestGetConversation:
    """Tests for get_conversation()."""

    @pytest.mark.unit
    def test_happy_path_returns_enriched(self, service, mock_supabase) -> None:
        """Returns enriched conversation with members, last message, unread count."""
        (
            _,
            conversations_mock,
            members_mock,
            messages_mock,
            users_mock,
            partnerships_mock,
        ) = mock_supabase

        conv = _make_conversation(conv_type="group")
        _setup_get_conversation(conversations_mock, [conv])
        _setup_verify_membership(members_mock, [_make_member_row(user_id=USER_A)])

        member_rows = [
            _make_member_row(user_id=USER_A),
            _make_member_row(user_id=USER_B),
        ]
        members_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=member_rows
        )

        _setup_users_lookup(
            users_mock,
            [
                _make_user_row(user_id=USER_A, username="alice"),
                _make_user_row(user_id=USER_B, username="bob"),
            ],
        )

        messages_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = service.get_conversation(CONV_ID, USER_A)

        assert result["id"] == CONV_ID
        assert result["type"] == "group"
        assert "members" in result
        assert "is_read_only" in result

    @pytest.mark.unit
    def test_not_found_raises(self, service, mock_supabase) -> None:
        """Raises ConversationNotFoundError when conversation doesn't exist."""
        _, conversations_mock, _, _, _, _ = mock_supabase

        _setup_get_conversation(conversations_mock, [])

        with pytest.raises(ConversationNotFoundError, match="not found"):
            service.get_conversation(CONV_ID, USER_A)

    @pytest.mark.unit
    def test_not_member_raises(self, service, mock_supabase) -> None:
        """Raises NotConversationMemberError when user is not a member."""
        _, conversations_mock, members_mock, _, _, _ = mock_supabase

        _setup_get_conversation(conversations_mock, [_make_conversation()])
        _setup_verify_membership(members_mock, [])

        with pytest.raises(NotConversationMemberError, match="not a member"):
            service.get_conversation(CONV_ID, USER_A)
