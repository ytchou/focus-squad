"""
Partner messaging models.

Aligned with design doc: output/plan/2026-02-12-partner-messaging-design.md
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    ALLOWED_REACTIONS,
    MESSAGE_MAX_LENGTH,
)

# ===========================================
# Enums
# ===========================================


class ConversationType(str, Enum):
    """Type of conversation."""

    DIRECT = "direct"
    GROUP = "group"


# ===========================================
# Request Models
# ===========================================


class CreateConversationRequest(BaseModel):
    """Create a new conversation (direct or group)."""

    type: ConversationType
    member_ids: list[str] = Field(..., min_length=1)
    name: Optional[str] = Field(None, max_length=100)


class SendMessageRequest(BaseModel):
    """Send a message to a conversation."""

    content: str = Field(..., min_length=1, max_length=MESSAGE_MAX_LENGTH)


class ToggleReactionRequest(BaseModel):
    """Toggle a reaction on a message."""

    emoji: str

    @classmethod
    def validate_emoji(cls, emoji: str) -> str:
        if emoji not in ALLOWED_REACTIONS:
            raise ValueError(f"Invalid reaction: {emoji}. Valid reactions: {ALLOWED_REACTIONS}")
        return emoji


class AddGroupMemberRequest(BaseModel):
    """Add a member to a group conversation."""

    user_id: str


# ===========================================
# Response Models
# ===========================================


class MessageSenderInfo(BaseModel):
    """Sender profile info embedded in messages."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    display_name: Optional[str] = None
    avatar_config: dict[str, Any] = Field(default_factory=dict)
    pixel_avatar_id: Optional[str] = None


class MessageInfo(BaseModel):
    """A single message."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    sender_id: str
    sender: Optional[MessageSenderInfo] = None
    content: str
    reactions: dict[str, list[str]] = Field(default_factory=dict)
    deleted_at: Optional[datetime] = None
    created_at: datetime


class ConversationMemberInfo(BaseModel):
    """A member in a conversation with read state."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    username: str
    display_name: Optional[str] = None
    avatar_config: dict[str, Any] = Field(default_factory=dict)
    pixel_avatar_id: Optional[str] = None
    last_read_at: Optional[datetime] = None


class ConversationInfo(BaseModel):
    """A conversation with metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    type: ConversationType
    name: Optional[str] = None
    members: list[ConversationMemberInfo] = Field(default_factory=list)
    last_message: Optional[MessageInfo] = None
    unread_count: int = 0
    is_read_only: bool = False
    updated_at: datetime


class ConversationListResponse(BaseModel):
    """Response for listing conversations."""

    conversations: list[ConversationInfo]


class MessagesResponse(BaseModel):
    """Paginated messages response."""

    messages: list[MessageInfo]
    has_more: bool = False
    next_cursor: Optional[str] = None


class SendMessageResponse(BaseModel):
    """Response after sending a message."""

    message: MessageInfo


class ConversationCreatedResponse(BaseModel):
    """Response after creating a conversation."""

    conversation: ConversationInfo


class ToggleReactionResponse(BaseModel):
    """Response after toggling a reaction."""

    message_id: str
    reactions: dict[str, list[str]]


class MarkReadResponse(BaseModel):
    """Response after marking a conversation as read."""

    conversation_id: str
    last_read_at: datetime


class AddGroupMemberResponse(BaseModel):
    """Response after adding a group member."""

    conversation_id: str
    user_id: str
    message: str = "Member added"


class LeaveGroupResponse(BaseModel):
    """Response after leaving a group."""

    message: str = "Left group"


class DeleteMessageResponse(BaseModel):
    """Response after deleting a message."""

    message_id: str
    message: str = "Message deleted"


# ===========================================
# Exception Classes
# ===========================================


class MessageServiceError(Exception):
    """Base exception for message service errors."""

    pass


class ConversationNotFoundError(MessageServiceError):
    """Conversation not found."""

    pass


class NotConversationMemberError(MessageServiceError):
    """User is not a member of this conversation."""

    pass


class ConversationLimitError(MessageServiceError):
    """Maximum number of conversations reached."""

    pass


class InvalidReactionError(MessageServiceError):
    """Invalid reaction emoji."""

    pass


class MessageNotFoundError(MessageServiceError):
    """Message not found."""

    pass


class NotMessageOwnerError(MessageServiceError):
    """User is not the sender of this message."""

    pass


class GroupSizeError(MessageServiceError):
    """Group size constraint violated (too many or too few members)."""

    pass


class NotMutualPartnersError(MessageServiceError):
    """Not all members are mutual partners."""

    pass


class ConversationReadOnlyError(MessageServiceError):
    """Conversation is read-only (e.g., partners un-partnered)."""

    pass


class DirectConversationExistsError(MessageServiceError):
    """A direct conversation already exists between these users."""

    pass
