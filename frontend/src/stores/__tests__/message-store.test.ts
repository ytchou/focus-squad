import { describe, it, expect, vi, beforeEach } from "vitest";
import { useMessageStore, MessageInfo } from "../message-store";

// Mock the API client
vi.mock("@/lib/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: vi.fn(),
}));

import { api } from "@/lib/api/client";

describe("message-store", () => {
  beforeEach(() => {
    // Reset store to initial state
    useMessageStore.setState({
      conversations: [],
      activeConversationId: null,
      messages: {},
      totalUnreadCount: 0,
      isLoadingConversations: false,
      isLoadingMessages: false,
      isSending: false,
      hasMore: {},
      cursors: {},
      error: null,
    });
    vi.clearAllMocks();
  });

  describe("openConversation cursor reset", () => {
    it("should clear previous conversation cursor when switching", async () => {
      // Setup: conversation A has messages and cursor
      useMessageStore.setState({
        activeConversationId: "conv-a",
        messages: { "conv-a": [{ id: "msg-1" }] as MessageInfo[] },
        cursors: { "conv-a": "cursor-a" },
        hasMore: { "conv-a": false },
      });

      // Mock API response for new conversation
      vi.mocked(api.get).mockResolvedValueOnce({
        messages: [{ id: "msg-2" }],
        has_more: true,
        next_cursor: "cursor-b",
      });
      vi.mocked(api.put).mockResolvedValueOnce({}); // markRead

      // Act: switch to conversation B
      await useMessageStore.getState().openConversation("conv-b");

      // Assert: conversation A cursor should be reset
      const state = useMessageStore.getState();
      expect(state.cursors["conv-a"]).toBeNull();
      expect(state.hasMore["conv-a"]).toBe(true);

      // Conversation B should have its new cursor
      expect(state.cursors["conv-b"]).toBe("cursor-b");
      expect(state.activeConversationId).toBe("conv-b");
    });

    it("should not reset cursor when opening same conversation", async () => {
      // Setup: already on conversation A
      useMessageStore.setState({
        activeConversationId: "conv-a",
        cursors: { "conv-a": "cursor-a" },
        hasMore: { "conv-a": false },
      });

      // Mock API response
      vi.mocked(api.get).mockResolvedValueOnce({
        messages: [],
        has_more: true,
        next_cursor: "cursor-a-new",
      });
      vi.mocked(api.put).mockResolvedValueOnce({});

      // Act: re-open same conversation
      await useMessageStore.getState().openConversation("conv-a");

      // Assert: cursor should be updated (not set to null first)
      const state = useMessageStore.getState();
      expect(state.cursors["conv-a"]).toBe("cursor-a-new");
    });

    it("should restore previous state on API failure", async () => {
      // Setup: conversation A has messages and cursor
      useMessageStore.setState({
        activeConversationId: "conv-a",
        messages: { "conv-a": [{ id: "msg-1" }] as MessageInfo[] },
        cursors: { "conv-a": "cursor-a" },
        hasMore: { "conv-a": false },
      });

      // Mock API failure for new conversation
      vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

      // Act: try to switch to conversation B
      await useMessageStore.getState().openConversation("conv-b");

      // Assert: should restore previous conversation state
      const state = useMessageStore.getState();
      expect(state.activeConversationId).toBe("conv-a");
      expect(state.cursors["conv-a"]).toBe("cursor-a");
      expect(state.hasMore["conv-a"]).toBe(false);
      expect(state.error).toBe("Network error");
    });
  });
});
