"""
Partner messaging service.

Handles:
- Creating direct (1-on-1) and group conversations
- Sending and retrieving messages with cursor-based pagination
- Read receipts (mark as read)
- Emoji reactions (toggle on/off)
- Message soft deletion
- Group membership management (add/leave)
- Read-only detection for un-partnered direct conversations

Design doc: output/plan/2026-02-12-partner-messaging-design.md
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from supabase import Client

from app.core.constants import (
    ALLOWED_REACTIONS,
    MAX_DIRECT_CONVERSATIONS,
    MAX_GROUP_CONVERSATIONS,
    MAX_GROUP_SIZE,
    MESSAGES_PAGE_SIZE,
    MIN_GROUP_SIZE,
)
from app.core.database import get_supabase
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

logger = logging.getLogger(__name__)

USER_PROFILE_FIELDS = "id, username, display_name, avatar_config, pixel_avatar_id"


class MessageService:
    """Service for partner direct messaging."""

    def __init__(self, supabase: Optional[Client] = None) -> None:
        self._supabase = supabase

    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    # =========================================================================
    # Public API
    # =========================================================================

    def create_direct_conversation(self, user_id: str, partner_id: str) -> dict:
        """
        Create a 1-on-1 conversation with a partner, or return existing one.

        Validates:
        - Users have an accepted partnership
        - No existing direct conversation between them
        - User hasn't hit MAX_DIRECT_CONVERSATIONS

        Returns:
            Conversation dict with members.

        Raises:
            NotMutualPartnersError: Not accepted partners
            ConversationLimitError: Too many direct conversations
            DirectConversationExistsError: Already have a direct conversation
        """
        self._validate_partnership(user_id, partner_id)

        existing = self._find_direct_conversation(user_id, partner_id)
        if existing:
            raise DirectConversationExistsError(
                "A direct conversation already exists between you and this partner"
            )

        direct_count = self._count_conversations(user_id, "direct")
        if direct_count >= MAX_DIRECT_CONVERSATIONS:
            raise ConversationLimitError(
                f"Maximum of {MAX_DIRECT_CONVERSATIONS} direct conversations reached"
            )

        now = datetime.now(timezone.utc).isoformat()

        conv_result = (
            self.supabase.table("conversations")
            .insert(
                {
                    "type": "direct",
                    "created_by": user_id,
                    "updated_at": now,
                }
            )
            .execute()
        )
        conversation = conv_result.data[0]

        self.supabase.table("conversation_members").insert(
            [
                {"conversation_id": conversation["id"], "user_id": user_id},
                {"conversation_id": conversation["id"], "user_id": partner_id},
            ]
        ).execute()

        return self._enrich_conversation(conversation, user_id)

    def create_group_conversation(self, creator_id: str, member_ids: list[str], name: str) -> dict:
        """
        Create a group conversation with selected partners.

        Validates:
        - All member_ids are mutual partners of creator
        - Group size is between MIN_GROUP_SIZE and MAX_GROUP_SIZE (including creator)
        - Creator hasn't hit MAX_GROUP_CONVERSATIONS

        Returns:
            Conversation dict with members.

        Raises:
            GroupSizeError: Too many or too few members
            NotMutualPartnersError: Not all members are mutual partners
            ConversationLimitError: Too many group conversations
        """
        all_member_ids = list(set([creator_id] + member_ids))
        total_size = len(all_member_ids)

        if total_size < MIN_GROUP_SIZE:
            raise GroupSizeError(f"Group must have at least {MIN_GROUP_SIZE} members")
        if total_size > MAX_GROUP_SIZE:
            raise GroupSizeError(f"Group cannot exceed {MAX_GROUP_SIZE} members")

        for mid in member_ids:
            if mid != creator_id:
                self._validate_partnership(creator_id, mid)

        group_count = self._count_conversations(creator_id, "group")
        if group_count >= MAX_GROUP_CONVERSATIONS:
            raise ConversationLimitError(
                f"Maximum of {MAX_GROUP_CONVERSATIONS} group conversations reached"
            )

        now = datetime.now(timezone.utc).isoformat()

        conv_result = (
            self.supabase.table("conversations")
            .insert(
                {
                    "type": "group",
                    "name": name,
                    "created_by": creator_id,
                    "updated_at": now,
                }
            )
            .execute()
        )
        conversation = conv_result.data[0]

        member_rows = [
            {"conversation_id": conversation["id"], "user_id": uid} for uid in all_member_ids
        ]
        self.supabase.table("conversation_members").insert(member_rows).execute()

        return self._enrich_conversation(conversation, creator_id)

    def list_conversations(self, user_id: str) -> list[dict]:
        """
        List all conversations for a user with last message and unread count.

        Returns conversations sorted by most recent activity (updated_at DESC).
        Direct conversations with un-partnered users are marked is_read_only=True.
        """
        memberships = (
            self.supabase.table("conversation_members")
            .select("conversation_id")
            .eq("user_id", user_id)
            .execute()
        )

        if not memberships.data:
            return []

        conv_ids = [m["conversation_id"] for m in memberships.data]

        conversations = (
            self.supabase.table("conversations")
            .select("*")
            .in_("id", conv_ids)
            .order("updated_at", desc=True)
            .execute()
        )

        if not conversations.data:
            return []

        return [self._enrich_conversation(conv, user_id) for conv in conversations.data]

    def get_messages(
        self,
        conversation_id: str,
        user_id: str,
        cursor: Optional[str] = None,
        limit: int = MESSAGES_PAGE_SIZE,
    ) -> dict:
        """
        Get paginated messages for a conversation (newest first).

        Uses cursor-based pagination on created_at.

        Returns:
            Dict with messages list, has_more flag, and next_cursor.

        Raises:
            ConversationNotFoundError: Conversation doesn't exist
            NotConversationMemberError: User is not a member
        """
        self._get_conversation(conversation_id)
        self._verify_membership(conversation_id, user_id)

        query = (
            self.supabase.table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at", desc=True)
            .limit(limit + 1)
        )

        if cursor:
            query = query.lt("created_at", cursor)

        result = query.execute()
        messages = result.data or []

        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]

        next_cursor = messages[-1]["created_at"] if messages and has_more else None

        sender_ids = list({m["sender_id"] for m in messages})
        sender_map = self._get_user_profiles(sender_ids) if sender_ids else {}

        enriched = []
        for msg in messages:
            msg["sender"] = sender_map.get(msg["sender_id"])
            if msg.get("deleted_at"):
                msg["content"] = ""
            enriched.append(msg)

        return {
            "messages": enriched,
            "has_more": has_more,
            "next_cursor": next_cursor,
        }

    def send_message(self, conversation_id: str, sender_id: str, content: str) -> dict:
        """
        Send a message to a conversation.

        Validates:
        - Sender is a member
        - Conversation is not read-only

        Returns:
            The created message dict with sender info.

        Raises:
            ConversationNotFoundError: Conversation doesn't exist
            NotConversationMemberError: User is not a member
            ConversationReadOnlyError: Conversation is read-only
        """
        conversation = self._get_conversation(conversation_id)
        self._verify_membership(conversation_id, sender_id)

        if self._is_read_only(conversation, sender_id):
            raise ConversationReadOnlyError(
                "This conversation is read-only because the partnership is no longer active"
            )

        now = datetime.now(timezone.utc).isoformat()

        msg_result = (
            self.supabase.table("messages")
            .insert(
                {
                    "conversation_id": conversation_id,
                    "sender_id": sender_id,
                    "content": content,
                    "created_at": now,
                }
            )
            .execute()
        )
        message = msg_result.data[0]

        self.supabase.table("conversations").update({"updated_at": now}).eq(
            "id", conversation_id
        ).execute()

        sender_map = self._get_user_profiles([sender_id])
        message["sender"] = sender_map.get(sender_id)

        return message

    def mark_read(self, conversation_id: str, user_id: str) -> dict:
        """
        Mark a conversation as read by updating last_read_at.

        Returns:
            Dict with conversation_id and last_read_at timestamp.

        Raises:
            ConversationNotFoundError: Conversation doesn't exist
            NotConversationMemberError: User is not a member
        """
        self._get_conversation(conversation_id)
        self._verify_membership(conversation_id, user_id)

        now = datetime.now(timezone.utc).isoformat()

        self.supabase.table("conversation_members").update({"last_read_at": now}).eq(
            "conversation_id", conversation_id
        ).eq("user_id", user_id).execute()

        return {"conversation_id": conversation_id, "last_read_at": now}

    def toggle_reaction(self, message_id: str, user_id: str, emoji: str) -> dict:
        """
        Toggle a reaction on a message.

        If user already reacted with this emoji, removes it.
        If not, adds it.

        Returns:
            Dict with message_id and updated reactions.

        Raises:
            InvalidReactionError: Emoji not in ALLOWED_REACTIONS
            MessageNotFoundError: Message doesn't exist
            NotConversationMemberError: User not in the conversation
        """
        if emoji not in ALLOWED_REACTIONS:
            raise InvalidReactionError(f"Invalid reaction: {emoji}. Allowed: {ALLOWED_REACTIONS}")

        message = self._get_message(message_id)
        self._verify_membership(message["conversation_id"], user_id)

        reactions = message.get("reactions") or {}
        users_for_emoji = reactions.get(emoji, [])

        if user_id in users_for_emoji:
            users_for_emoji.remove(user_id)
            if not users_for_emoji:
                reactions.pop(emoji, None)
            else:
                reactions[emoji] = users_for_emoji
        else:
            users_for_emoji.append(user_id)
            reactions[emoji] = users_for_emoji

        self.supabase.table("messages").update({"reactions": reactions}).eq(
            "id", message_id
        ).execute()

        return {"message_id": message_id, "reactions": reactions}

    def delete_message(self, message_id: str, user_id: str) -> None:
        """
        Soft-delete a message (sender only).

        Sets deleted_at timestamp. Content is blanked on read.

        Raises:
            MessageNotFoundError: Message doesn't exist
            NotMessageOwnerError: User is not the sender
        """
        message = self._get_message(message_id)

        if message["sender_id"] != user_id:
            raise NotMessageOwnerError("You can only delete your own messages")

        now = datetime.now(timezone.utc).isoformat()
        self.supabase.table("messages").update({"deleted_at": now}).eq("id", message_id).execute()

    def add_group_member(self, conversation_id: str, adder_id: str, new_member_id: str) -> None:
        """
        Add a member to a group conversation.

        Validates:
        - Conversation is a group
        - Adder is a member
        - New member is a partner of adder
        - Group isn't full

        Raises:
            ConversationNotFoundError: Conversation doesn't exist
            NotConversationMemberError: Adder is not a member
            NotMutualPartnersError: New member is not a partner
            GroupSizeError: Group is full
        """
        conversation = self._get_conversation(conversation_id)

        if conversation["type"] != "group":
            raise ConversationNotFoundError("Can only add members to group conversations")

        self._verify_membership(conversation_id, adder_id)
        self._validate_partnership(adder_id, new_member_id)

        members = (
            self.supabase.table("conversation_members")
            .select("user_id")
            .eq("conversation_id", conversation_id)
            .execute()
        )
        current_member_ids = [m["user_id"] for m in members.data]

        if new_member_id in current_member_ids:
            return

        if len(current_member_ids) >= MAX_GROUP_SIZE:
            raise GroupSizeError(f"Group cannot exceed {MAX_GROUP_SIZE} members")

        self.supabase.table("conversation_members").insert(
            {
                "conversation_id": conversation_id,
                "user_id": new_member_id,
            }
        ).execute()

    def leave_group(self, conversation_id: str, user_id: str) -> None:
        """
        Leave a group conversation.

        If the group drops below MIN_GROUP_SIZE, remaining members are also removed
        and the conversation is effectively dissolved.

        Raises:
            ConversationNotFoundError: Conversation doesn't exist or not a group
            NotConversationMemberError: User is not a member
        """
        conversation = self._get_conversation(conversation_id)

        if conversation["type"] != "group":
            raise ConversationNotFoundError("Can only leave group conversations")

        self._verify_membership(conversation_id, user_id)

        self.supabase.table("conversation_members").delete().eq(
            "conversation_id", conversation_id
        ).eq("user_id", user_id).execute()

        remaining = (
            self.supabase.table("conversation_members")
            .select("user_id", count="exact")
            .eq("conversation_id", conversation_id)
            .execute()
        )

        if (remaining.count or 0) < MIN_GROUP_SIZE:
            self.supabase.table("conversation_members").delete().eq(
                "conversation_id", conversation_id
            ).execute()
            logger.info(
                "Dissolved group %s (below minimum size after member left)",
                conversation_id,
            )

    def get_conversation(self, conversation_id: str, user_id: str) -> dict:
        """
        Get a single conversation with metadata.

        Raises:
            ConversationNotFoundError: Conversation doesn't exist
            NotConversationMemberError: User is not a member
        """
        conversation = self._get_conversation(conversation_id)
        self._verify_membership(conversation_id, user_id)
        return self._enrich_conversation(conversation, user_id)

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _get_conversation(self, conversation_id: str) -> dict:
        """Fetch a conversation by ID. Raises if not found."""
        result = (
            self.supabase.table("conversations").select("*").eq("id", conversation_id).execute()
        )

        if not result.data:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

        return result.data[0]

    def _verify_membership(self, conversation_id: str, user_id: str) -> None:
        """Verify user is a member of the conversation."""
        result = (
            self.supabase.table("conversation_members")
            .select("user_id")
            .eq("conversation_id", conversation_id)
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data:
            raise NotConversationMemberError("You are not a member of this conversation")

    def _get_message(self, message_id: str) -> dict:
        """Fetch a message by ID. Raises if not found."""
        result = self.supabase.table("messages").select("*").eq("id", message_id).execute()

        if not result.data:
            raise MessageNotFoundError(f"Message {message_id} not found")

        return result.data[0]

    def _find_direct_conversation(self, user_a_id: str, user_b_id: str) -> Optional[dict]:
        """Find an existing direct conversation between two users."""
        a_convs = (
            self.supabase.table("conversation_members")
            .select("conversation_id")
            .eq("user_id", user_a_id)
            .execute()
        )

        if not a_convs.data:
            return None

        a_conv_ids = [m["conversation_id"] for m in a_convs.data]

        shared = (
            self.supabase.table("conversation_members")
            .select("conversation_id")
            .eq("user_id", user_b_id)
            .in_("conversation_id", a_conv_ids)
            .execute()
        )

        if not shared.data:
            return None

        shared_ids = [m["conversation_id"] for m in shared.data]

        direct = (
            self.supabase.table("conversations")
            .select("*")
            .in_("id", shared_ids)
            .eq("type", "direct")
            .execute()
        )

        if not direct.data:
            return None

        return direct.data[0]

    def _validate_partnership(self, user_a_id: str, user_b_id: str) -> None:
        """Validate that two users have an accepted partnership."""
        result = (
            self.supabase.table("partnerships")
            .select("id, status")
            .or_(
                f"and(requester_id.eq.{user_a_id},addressee_id.eq.{user_b_id}),"
                f"and(requester_id.eq.{user_b_id},addressee_id.eq.{user_a_id})"
            )
            .eq("status", "accepted")
            .execute()
        )

        if not result.data:
            raise NotMutualPartnersError("You must be mutual partners to start a conversation")

    def _is_read_only(self, conversation: dict, user_id: str) -> bool:
        """
        Check if a conversation is read-only.

        Direct conversations become read-only when the partnership is no longer active.
        Group conversations are never read-only.
        """
        if conversation["type"] != "direct":
            return False

        members = (
            self.supabase.table("conversation_members")
            .select("user_id")
            .eq("conversation_id", conversation["id"])
            .execute()
        )

        member_ids = [m["user_id"] for m in members.data]
        other_id = next((mid for mid in member_ids if mid != user_id), None)

        if not other_id:
            return True

        result = (
            self.supabase.table("partnerships")
            .select("id")
            .or_(
                f"and(requester_id.eq.{user_id},addressee_id.eq.{other_id}),"
                f"and(requester_id.eq.{other_id},addressee_id.eq.{user_id})"
            )
            .eq("status", "accepted")
            .execute()
        )

        return not result.data

    def _count_conversations(self, user_id: str, conv_type: str) -> int:
        """Count conversations of a given type for a user."""
        memberships = (
            self.supabase.table("conversation_members")
            .select("conversation_id")
            .eq("user_id", user_id)
            .execute()
        )

        if not memberships.data:
            return 0

        conv_ids = [m["conversation_id"] for m in memberships.data]

        result = (
            self.supabase.table("conversations")
            .select("id", count="exact")
            .in_("id", conv_ids)
            .eq("type", conv_type)
            .execute()
        )

        return result.count or 0

    def _get_user_profiles(self, user_ids: list[str]) -> dict[str, dict]:
        """Fetch user profiles by IDs. Returns a map of user_id -> profile dict."""
        if not user_ids:
            return {}

        result = (
            self.supabase.table("users").select(USER_PROFILE_FIELDS).in_("id", user_ids).execute()
        )

        return {
            u["id"]: {
                "user_id": u["id"],
                "username": u["username"],
                "display_name": u.get("display_name"),
                "avatar_config": u.get("avatar_config") or {},
                "pixel_avatar_id": u.get("pixel_avatar_id"),
            }
            for u in result.data
        }

    def _enrich_conversation(self, conversation: dict, user_id: str) -> dict:
        """
        Enrich a conversation with members, last message, unread count,
        and read-only status.
        """
        members_result = (
            self.supabase.table("conversation_members")
            .select("user_id, last_read_at")
            .eq("conversation_id", conversation["id"])
            .execute()
        )
        member_rows = members_result.data or []
        member_ids = [m["user_id"] for m in member_rows]
        last_read_map = {m["user_id"]: m["last_read_at"] for m in member_rows}

        profiles = self._get_user_profiles(member_ids)

        members = []
        for mid in member_ids:
            profile = profiles.get(mid, {})
            members.append(
                {
                    **profile,
                    "user_id": mid,
                    "last_read_at": last_read_map.get(mid),
                }
            )

        last_msg_result = (
            self.supabase.table("messages")
            .select("*")
            .eq("conversation_id", conversation["id"])
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        last_message = last_msg_result.data[0] if last_msg_result.data else None

        if last_message:
            sender_profiles = self._get_user_profiles([last_message["sender_id"]])
            last_message["sender"] = sender_profiles.get(last_message["sender_id"])
            if last_message.get("deleted_at"):
                last_message["content"] = ""

        user_last_read = last_read_map.get(user_id)
        unread_count = 0
        if user_last_read:
            unread_result = (
                self.supabase.table("messages")
                .select("id", count="exact")
                .eq("conversation_id", conversation["id"])
                .gt("created_at", user_last_read)
                .neq("sender_id", user_id)
                .execute()
            )
            unread_count = unread_result.count or 0

        is_read_only = self._is_read_only(conversation, user_id)

        return {
            "id": conversation["id"],
            "type": conversation["type"],
            "name": conversation.get("name"),
            "members": members,
            "last_message": last_message,
            "unread_count": unread_count,
            "is_read_only": is_read_only,
            "updated_at": conversation["updated_at"],
        }
