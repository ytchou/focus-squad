import { create } from "zustand";
import { api } from "@/lib/api/client";
import { toast } from "sonner";

// =============================================================================
// Types
// =============================================================================

export interface MessageSenderInfo {
  user_id: string;
  username: string;
  display_name: string | null;
  avatar_config: Record<string, unknown>;
  pixel_avatar_id: string | null;
}

export interface MessageInfo {
  id: string;
  conversation_id: string;
  sender_id: string;
  sender: MessageSenderInfo | null;
  content: string;
  reactions: Record<string, string[]>;
  deleted_at: string | null;
  created_at: string;
}

export interface ConversationMemberInfo {
  user_id: string;
  username: string;
  display_name: string | null;
  avatar_config: Record<string, unknown>;
  pixel_avatar_id: string | null;
  last_read_at: string | null;
}

export interface ConversationInfo {
  id: string;
  type: "direct" | "group";
  name: string | null;
  members: ConversationMemberInfo[];
  last_message: MessageInfo | null;
  unread_count: number;
  is_read_only: boolean;
  updated_at: string;
}

// =============================================================================
// Store
// =============================================================================

interface MessageState {
  conversations: ConversationInfo[];
  activeConversationId: string | null;
  messages: Record<string, MessageInfo[]>;
  totalUnreadCount: number;
  isLoadingConversations: boolean;
  isLoadingMessages: boolean;
  isSending: boolean;
  hasMore: Record<string, boolean>;
  cursors: Record<string, string | null>;
  error: string | null;

  fetchConversations: () => Promise<void>;
  openConversation: (id: string) => Promise<void>;
  sendMessage: (conversationId: string, content: string) => Promise<void>;
  toggleReaction: (messageId: string, emoji: string) => Promise<void>;
  markRead: (conversationId: string) => Promise<void>;
  createDirectChat: (partnerId: string) => Promise<string>;
  createGroupChat: (memberIds: string[], name: string) => Promise<string>;
  deleteMessage: (messageId: string) => Promise<void>;
  loadMoreMessages: (conversationId: string) => Promise<void>;
  leaveGroup: (conversationId: string) => Promise<void>;

  handleNewMessage: (message: MessageInfo) => void;
  handleReadUpdate: (conversationId: string, userId: string, lastReadAt: string) => void;

  reset: () => void;
}

const initialState = {
  conversations: [] as ConversationInfo[],
  activeConversationId: null as string | null,
  messages: {} as Record<string, MessageInfo[]>,
  totalUnreadCount: 0,
  isLoadingConversations: false,
  isLoadingMessages: false,
  isSending: false,
  hasMore: {} as Record<string, boolean>,
  cursors: {} as Record<string, string | null>,
  error: null as string | null,
};

export const useMessageStore = create<MessageState>()((set, get) => ({
  ...initialState,

  fetchConversations: async () => {
    set({ isLoadingConversations: true, error: null });
    try {
      const data = await api.get<{ conversations: ConversationInfo[] }>("/api/v1/messages/");
      const conversations = data.conversations;
      const totalUnreadCount = conversations.reduce((sum, c) => sum + c.unread_count, 0);
      set({ conversations, totalUnreadCount, isLoadingConversations: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load conversations";
      set({ error: message, isLoadingConversations: false });
    }
  },

  openConversation: async (id: string) => {
    const prevId = get().activeConversationId;

    // Clear pagination state for previous conversation to ensure fresh data on return
    if (prevId && prevId !== id) {
      set((state) => ({
        cursors: { ...state.cursors, [prevId]: null },
        hasMore: { ...state.hasMore, [prevId]: true },
      }));
    }

    set({ activeConversationId: id, isLoadingMessages: true });

    try {
      const data = await api.get<{
        messages: MessageInfo[];
        has_more: boolean;
        next_cursor: string | null;
      }>(`/api/v1/messages/${id}/messages`);

      set((state) => ({
        messages: { ...state.messages, [id]: data.messages },
        hasMore: { ...state.hasMore, [id]: data.has_more },
        cursors: { ...state.cursors, [id]: data.next_cursor },
        isLoadingMessages: false,
      }));

      await get().markRead(id);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load messages";
      set({ error: message, isLoadingMessages: false });
    }
  },

  sendMessage: async (conversationId: string, content: string) => {
    set({ isSending: true, error: null });
    try {
      const data = await api.post<{ message: MessageInfo }>(
        `/api/v1/messages/${conversationId}/messages`,
        { content }
      );

      set((state) => {
        const existing = state.messages[conversationId] || [];

        // Optimistically update conversation list: set last_message and re-sort
        const conversations = state.conversations
          .map((c) =>
            c.id === conversationId
              ? { ...c, last_message: data.message, updated_at: data.message.created_at }
              : c
          )
          .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());

        return {
          messages: {
            ...state.messages,
            [conversationId]: [data.message, ...existing],
          },
          conversations,
          isSending: false,
        };
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to send message";
      set({ error: message, isSending: false });
    }
  },

  toggleReaction: async (messageId: string, emoji: string) => {
    const { activeConversationId } = get();
    if (!activeConversationId) return;

    try {
      const data = await api.post<{
        message_id: string;
        reactions: Record<string, string[]>;
      }>(`/api/v1/messages/reactions/${messageId}`, { emoji });

      set((state) => {
        const convMessages = state.messages[activeConversationId] || [];
        return {
          messages: {
            ...state.messages,
            [activeConversationId]: convMessages.map((m) =>
              m.id === messageId ? { ...m, reactions: data.reactions } : m
            ),
          },
        };
      });
    } catch {
      // Silent fail for reactions
    }
  },

  markRead: async (conversationId: string) => {
    try {
      await api.put(`/api/v1/messages/${conversationId}/read`);

      set((state) => {
        const conversations = state.conversations.map((c) =>
          c.id === conversationId ? { ...c, unread_count: 0 } : c
        );
        const totalUnreadCount = conversations.reduce((sum, c) => sum + c.unread_count, 0);
        return { conversations, totalUnreadCount };
      });
    } catch {
      // Non-critical
    }
  },

  createDirectChat: async (partnerId: string) => {
    set({ error: null });
    try {
      const data = await api.post<{ conversation: ConversationInfo }>("/api/v1/messages/", {
        type: "direct",
        member_ids: [partnerId],
      });
      await get().fetchConversations();
      return data.conversation.id;
    } catch (err) {
      // If conversation already exists, find it locally or refetch to find it
      if (err instanceof Error && err.message.includes("already exists")) {
        // First check local state
        let existing = get().conversations.find(
          (c) => c.type === "direct" && c.members.some((m) => m.user_id === partnerId)
        );
        if (existing) return existing.id;

        // Local state may be stale — refetch and try again
        await get().fetchConversations();
        existing = get().conversations.find(
          (c) => c.type === "direct" && c.members.some((m) => m.user_id === partnerId)
        );
        if (existing) return existing.id;
      }
      const message = err instanceof Error ? err.message : "Failed to create conversation";
      set({ error: message });
      throw err;
    }
  },

  createGroupChat: async (memberIds: string[], name: string) => {
    set({ error: null });
    try {
      const data = await api.post<{ conversation: ConversationInfo }>("/api/v1/messages/", {
        type: "group",
        member_ids: memberIds,
        name,
      });
      await get().fetchConversations();
      return data.conversation.id;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create group";
      set({ error: message });
      throw err;
    }
  },

  deleteMessage: async (messageId: string) => {
    const { activeConversationId } = get();
    if (!activeConversationId) return;

    try {
      await api.delete(`/api/v1/messages/msg/${messageId}`);

      set((state) => {
        const convMessages = state.messages[activeConversationId] || [];
        return {
          messages: {
            ...state.messages,
            [activeConversationId]: convMessages.map((m) =>
              m.id === messageId ? { ...m, deleted_at: new Date().toISOString(), content: "" } : m
            ),
          },
        };
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to delete message";
      set({ error: message });
    }
  },

  loadMoreMessages: async (conversationId: string) => {
    const { hasMore, cursors, isLoadingMessages } = get();
    if (!hasMore[conversationId] || isLoadingMessages) return;

    const cursor = cursors[conversationId];
    if (!cursor) return;

    set({ isLoadingMessages: true });
    try {
      const data = await api.get<{
        messages: MessageInfo[];
        has_more: boolean;
        next_cursor: string | null;
      }>(`/api/v1/messages/${conversationId}/messages?cursor=${cursor}`);

      set((state) => {
        const existing = state.messages[conversationId] || [];
        return {
          messages: {
            ...state.messages,
            [conversationId]: [...existing, ...data.messages],
          },
          hasMore: { ...state.hasMore, [conversationId]: data.has_more },
          cursors: { ...state.cursors, [conversationId]: data.next_cursor },
          isLoadingMessages: false,
        };
      });
    } catch {
      set({ isLoadingMessages: false });
    }
  },

  leaveGroup: async (conversationId: string) => {
    try {
      await api.delete(`/api/v1/messages/${conversationId}/leave`);
      set((state) => ({
        conversations: state.conversations.filter((c) => c.id !== conversationId),
        activeConversationId:
          state.activeConversationId === conversationId ? null : state.activeConversationId,
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to leave group";
      set({ error: message });
    }
  },

  // Called by Supabase Realtime hook when a new message arrives
  handleNewMessage: (message: MessageInfo) => {
    const { activeConversationId } = get();
    const convId = message.conversation_id;

    set((state) => {
      // Add message to the conversation's message list
      const existing = state.messages[convId] || [];
      const messages = {
        ...state.messages,
        [convId]: [message, ...existing],
      };

      // Update conversation in list
      const conversations = state.conversations.map((c) => {
        if (c.id !== convId) return c;
        const isActive = activeConversationId === convId;
        return {
          ...c,
          last_message: message,
          unread_count: isActive ? c.unread_count : c.unread_count + 1,
          updated_at: message.created_at,
        };
      });

      // Re-sort by updated_at
      conversations.sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );

      const totalUnreadCount = conversations.reduce((sum, c) => sum + c.unread_count, 0);

      return { messages, conversations, totalUnreadCount };
    });

    if (activeConversationId === convId) {
      // Message arrived for active conversation — update server-side read receipt
      get().markRead(convId);
    } else {
      // Show toast for messages in other conversations
      const senderName = message.sender?.display_name || message.sender?.username || "New message";
      toast(senderName, {
        description: message.content.slice(0, 80),
      });
    }
  },

  // Called by Supabase Realtime hook when a read receipt update arrives
  handleReadUpdate: (conversationId: string, userId: string, lastReadAt: string) => {
    set((state) => ({
      conversations: state.conversations.map((c) => {
        if (c.id !== conversationId) return c;
        return {
          ...c,
          members: c.members.map((m) =>
            m.user_id === userId ? { ...m, last_read_at: lastReadAt } : m
          ),
        };
      }),
    }));
  },

  reset: () => set(initialState),
}));
