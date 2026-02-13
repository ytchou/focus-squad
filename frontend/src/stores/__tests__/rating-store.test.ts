import { describe, it, expect, vi, beforeEach } from "vitest";
import { useRatingStore } from "../rating-store";

// Mock the API client
vi.mock("@/lib/api/client", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

describe("rating-store", () => {
  beforeEach(() => {
    // Reset store state
    useRatingStore.getState().reset();
    vi.clearAllMocks();
  });

  describe("setPendingRatings", () => {
    it("initializes ratings for all users", () => {
      const store = useRatingStore.getState();

      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
        { user_id: "user-2", username: "bob", display_name: "Bob", avatar_config: {} },
      ]);

      const state = useRatingStore.getState();
      expect(state.hasPendingRatings).toBe(true);
      expect(state.pendingSessionId).toBe("session-123");
      expect(state.rateableUsers).toHaveLength(2);
      expect(state.ratings["user-1"]).toEqual({ value: null, reasons: [], otherReasonText: "" });
      expect(state.ratings["user-2"]).toEqual({ value: null, reasons: [], otherReasonText: "" });
      expect(state.error).toBeNull();
    });
  });

  describe("setRating", () => {
    it("sets rating value for a user", () => {
      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);

      store.setRating("user-1", "green");

      expect(useRatingStore.getState().ratings["user-1"].value).toBe("green");
    });

    it("clears reasons when switching away from red", () => {
      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);

      // Set red with reasons
      store.setRating("user-1", "red");
      store.setReasons("user-1", ["disruptive", "other"]);
      store.setOtherText("user-1", "was rude");

      // Switch to green - should clear reasons
      store.setRating("user-1", "green");

      const state = useRatingStore.getState();
      expect(state.ratings["user-1"].value).toBe("green");
      expect(state.ratings["user-1"].reasons).toEqual([]);
      expect(state.ratings["user-1"].otherReasonText).toBe("");
    });

    it("preserves reasons when staying on red", () => {
      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);

      store.setRating("user-1", "red");
      store.setReasons("user-1", ["disruptive"]);
      store.setRating("user-1", "red"); // Set again

      expect(useRatingStore.getState().ratings["user-1"].reasons).toEqual(["disruptive"]);
    });
  });

  describe("setReasons", () => {
    it("sets reasons for a user", () => {
      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);

      store.setReasons("user-1", ["disruptive", "no_show"]);

      expect(useRatingStore.getState().ratings["user-1"].reasons).toEqual([
        "disruptive",
        "no_show",
      ]);
    });

    it("clears other text when 'other' reason is deselected", () => {
      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);

      store.setReasons("user-1", ["other"]);
      store.setOtherText("user-1", "custom reason");
      store.setReasons("user-1", ["disruptive"]); // Remove "other"

      expect(useRatingStore.getState().ratings["user-1"].otherReasonText).toBe("");
    });

    it("preserves other text when 'other' reason remains selected", () => {
      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);

      store.setReasons("user-1", ["other"]);
      store.setOtherText("user-1", "custom reason");
      store.setReasons("user-1", ["disruptive", "other"]);

      expect(useRatingStore.getState().ratings["user-1"].otherReasonText).toBe("custom reason");
    });
  });

  describe("setOtherText", () => {
    it("sets other reason text for a user", () => {
      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);

      store.setOtherText("user-1", "was very distracting");

      expect(useRatingStore.getState().ratings["user-1"].otherReasonText).toBe(
        "was very distracting"
      );
    });
  });

  describe("submitRatings", () => {
    it("proceeds when sessionId matches pendingSessionId", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post).mockResolvedValueOnce({});

      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);
      store.setRating("user-1", "green");

      await store.submitRatings("session-123");

      expect(mockPost).toHaveBeenCalledWith(
        "/api/v1/sessions/session-123/rate",
        expect.any(Object)
      );
      expect(useRatingStore.getState().error).toBeNull();
    });

    it("sets error when sessionId does not match pendingSessionId", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post);
      mockPost.mockClear();

      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);

      await store.submitRatings("session-456");

      expect(mockPost).not.toHaveBeenCalled();
      expect(useRatingStore.getState().error).toBe(
        "Session mismatch: cannot rate a different session"
      );
    });

    it("proceeds when no pendingSessionId is set (edge case)", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post).mockResolvedValueOnce({});

      const store = useRatingStore.getState();
      await store.submitRatings("session-123");

      expect(mockPost).toHaveBeenCalled();
    });

    it("includes reasons and other text for red ratings", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post).mockResolvedValueOnce({});

      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);
      store.setRating("user-1", "red");
      store.setReasons("user-1", ["disruptive", "other"]);
      store.setOtherText("user-1", "was rude");

      await store.submitRatings("session-123");

      expect(mockPost).toHaveBeenCalledWith("/api/v1/sessions/session-123/rate", {
        ratings: [
          {
            ratee_id: "user-1",
            rating: "red",
            reasons: ["disruptive", "other"],
            other_reason_text: "was rude",
          },
        ],
      });
    });

    it("filters out users with null ratings", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post).mockResolvedValueOnce({});

      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
        { user_id: "user-2", username: "bob", display_name: "Bob", avatar_config: {} },
      ]);
      store.setRating("user-1", "green");
      // user-2 has null rating

      await store.submitRatings("session-123");

      expect(mockPost).toHaveBeenCalledWith("/api/v1/sessions/session-123/rate", {
        ratings: [{ ratee_id: "user-1", rating: "green" }],
      });
    });

    it("resets state after successful submission", async () => {
      const { api } = await import("@/lib/api/client");
      vi.mocked(api.post).mockResolvedValueOnce({});

      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);
      store.setRating("user-1", "green");

      await store.submitRatings("session-123");

      const state = useRatingStore.getState();
      expect(state.hasPendingRatings).toBe(false);
      expect(state.pendingSessionId).toBeNull();
      expect(state.rateableUsers).toEqual([]);
    });

    it("sets error on API failure", async () => {
      const { api } = await import("@/lib/api/client");
      vi.mocked(api.post).mockRejectedValueOnce(new Error("Network error"));

      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);
      store.setRating("user-1", "green");

      await store.submitRatings("session-123");

      expect(useRatingStore.getState().error).toBe("Network error");
      expect(useRatingStore.getState().isSubmitting).toBe(false);
    });

    it("handles non-Error exceptions gracefully", async () => {
      const { api } = await import("@/lib/api/client");
      vi.mocked(api.post).mockRejectedValueOnce("string error");

      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);
      store.setRating("user-1", "green");

      await store.submitRatings("session-123");

      expect(useRatingStore.getState().error).toBe("Failed to submit ratings");
    });
  });

  describe("skipAll", () => {
    it("sets error when sessionId does not match pendingSessionId", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post);
      mockPost.mockClear();

      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);

      await store.skipAll("session-456");

      expect(mockPost).not.toHaveBeenCalled();
      expect(useRatingStore.getState().error).toBe(
        "Session mismatch: cannot rate a different session"
      );
    });

    it("calls skip endpoint with correct session", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post).mockResolvedValueOnce({});

      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);

      await store.skipAll("session-123");

      expect(mockPost).toHaveBeenCalledWith("/api/v1/sessions/session-123/rate/skip");
    });

    it("resets state after successful skip", async () => {
      const { api } = await import("@/lib/api/client");
      vi.mocked(api.post).mockResolvedValueOnce({});

      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);

      await store.skipAll("session-123");

      const state = useRatingStore.getState();
      expect(state.hasPendingRatings).toBe(false);
      expect(state.pendingSessionId).toBeNull();
    });

    it("sets error on API failure", async () => {
      const { api } = await import("@/lib/api/client");
      vi.mocked(api.post).mockRejectedValueOnce(new Error("Network error"));

      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);

      await store.skipAll("session-123");

      expect(useRatingStore.getState().error).toBe("Network error");
    });

    it("handles non-Error exceptions gracefully", async () => {
      const { api } = await import("@/lib/api/client");
      vi.mocked(api.post).mockRejectedValueOnce("string error");

      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);

      await store.skipAll("session-123");

      expect(useRatingStore.getState().error).toBe("Failed to skip ratings");
    });
  });

  describe("checkPendingRatings", () => {
    it("sets pending ratings when API returns pending data", async () => {
      const { api } = await import("@/lib/api/client");
      vi.mocked(api.get).mockResolvedValueOnce({
        has_pending: true,
        pending: {
          session_id: "session-abc",
          rateable_users: [
            { user_id: "u1", username: "test", display_name: "Test", avatar_config: {} },
          ],
          expires_at: "2026-02-13T12:00:00Z",
        },
      });

      const store = useRatingStore.getState();
      await store.checkPendingRatings();

      const state = useRatingStore.getState();
      expect(state.hasPendingRatings).toBe(true);
      expect(state.pendingSessionId).toBe("session-abc");
      expect(state.rateableUsers).toHaveLength(1);
    });

    it("clears pending state when API returns no pending", async () => {
      const { api } = await import("@/lib/api/client");
      vi.mocked(api.get).mockResolvedValueOnce({
        has_pending: false,
        pending: null,
      });

      const store = useRatingStore.getState();
      store.setPendingRatings("old-session", [
        { user_id: "u1", username: "test", display_name: "Test", avatar_config: {} },
      ]);

      await store.checkPendingRatings();

      const state = useRatingStore.getState();
      expect(state.hasPendingRatings).toBe(false);
      expect(state.pendingSessionId).toBeNull();
    });

    it("clears pending state when rateable_users is empty", async () => {
      const { api } = await import("@/lib/api/client");
      vi.mocked(api.get).mockResolvedValueOnce({
        has_pending: true,
        pending: {
          session_id: "session-abc",
          rateable_users: [],
          expires_at: "2026-02-13T12:00:00Z",
        },
      });

      const store = useRatingStore.getState();
      await store.checkPendingRatings();

      const state = useRatingStore.getState();
      expect(state.hasPendingRatings).toBe(false);
    });

    it("silently handles API errors", async () => {
      const { api } = await import("@/lib/api/client");
      vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

      const store = useRatingStore.getState();
      // Should not throw
      await store.checkPendingRatings();

      // State should remain unchanged
      expect(useRatingStore.getState().error).toBeNull();
    });
  });

  describe("fetchRatingHistory", () => {
    it("fetches first page of rating history", async () => {
      const { api } = await import("@/lib/api/client");
      vi.mocked(api.get).mockResolvedValueOnce({
        summary: { total_received: 10, green_count: 8, red_count: 2, green_percentage: 80 },
        items: [{ id: "1", session_id: "s1", rating: "green", created_at: "2026-02-13" }],
        total: 10,
        page: 1,
        per_page: 20,
      });

      const store = useRatingStore.getState();
      await store.fetchRatingHistory();

      const state = useRatingStore.getState();
      expect(state.ratingHistory).not.toBeNull();
      expect(state.ratingHistory?.items).toHaveLength(1);
      expect(state.isLoadingHistory).toBe(false);
    });

    it("appends items for subsequent pages", async () => {
      const { api } = await import("@/lib/api/client");

      // First page
      vi.mocked(api.get).mockResolvedValueOnce({
        summary: { total_received: 10, green_count: 8, red_count: 2, green_percentage: 80 },
        items: [{ id: "1", session_id: "s1", rating: "green", created_at: "2026-02-13" }],
        total: 10,
        page: 1,
        per_page: 20,
      });

      const store = useRatingStore.getState();
      await store.fetchRatingHistory(1);

      // Second page
      vi.mocked(api.get).mockResolvedValueOnce({
        summary: { total_received: 10, green_count: 8, red_count: 2, green_percentage: 80 },
        items: [{ id: "2", session_id: "s2", rating: "red", created_at: "2026-02-12" }],
        total: 10,
        page: 2,
        per_page: 20,
      });

      await useRatingStore.getState().fetchRatingHistory(2);

      const state = useRatingStore.getState();
      expect(state.ratingHistory?.items).toHaveLength(2);
    });

    it("handles API errors gracefully", async () => {
      const { api } = await import("@/lib/api/client");
      vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

      const store = useRatingStore.getState();
      await store.fetchRatingHistory();

      expect(useRatingStore.getState().isLoadingHistory).toBe(false);
    });
  });

  describe("reset", () => {
    it("resets all state to initial values", () => {
      const store = useRatingStore.getState();
      store.setPendingRatings("session-123", [
        { user_id: "user-1", username: "alice", display_name: "Alice", avatar_config: {} },
      ]);
      store.setRating("user-1", "green");

      store.reset();

      const state = useRatingStore.getState();
      expect(state.hasPendingRatings).toBe(false);
      expect(state.pendingSessionId).toBeNull();
      expect(state.rateableUsers).toEqual([]);
      expect(state.ratings).toEqual({});
      expect(state.isSubmitting).toBe(false);
      expect(state.error).toBeNull();
    });
  });
});
