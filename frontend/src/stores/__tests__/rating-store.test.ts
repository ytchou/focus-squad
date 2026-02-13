import { describe, it, expect, vi, beforeEach } from "vitest";
import { useRatingStore } from "../rating-store";

// Mock the API client
vi.mock("@/lib/api/client", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

describe("rating-store sessionId validation", () => {
  beforeEach(() => {
    // Reset store state
    useRatingStore.getState().reset();
  });

  describe("submitRatings", () => {
    it("proceeds when sessionId matches pendingSessionId", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post).mockResolvedValueOnce({});

      const store = useRatingStore.getState();

      // Set up pending ratings for session-123
      store.setPendingRatings("session-123", [
        {
          user_id: "user-1",
          username: "alice",
          display_name: "Alice",
          avatar_config: {},
        },
      ]);

      // Set a rating
      store.setRating("user-1", "green");

      // Submit with matching sessionId
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

      // Set up pending ratings for session-123
      store.setPendingRatings("session-123", [
        {
          user_id: "user-1",
          username: "alice",
          display_name: "Alice",
          avatar_config: {},
        },
      ]);

      // Try to submit for different session
      await store.submitRatings("session-456");

      // Should NOT call API
      expect(mockPost).not.toHaveBeenCalled();

      // Should set error
      expect(useRatingStore.getState().error).toBe(
        "Session mismatch: cannot rate a different session"
      );
    });

    it("proceeds when no pendingSessionId is set (edge case)", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post).mockResolvedValueOnce({});

      const store = useRatingStore.getState();

      // No pending ratings set, but try to submit anyway
      // This is an edge case - should proceed and let backend validate
      await store.submitRatings("session-123");

      expect(mockPost).toHaveBeenCalled();
    });
  });

  describe("skipAll", () => {
    it("sets error when sessionId does not match pendingSessionId", async () => {
      const { api } = await import("@/lib/api/client");
      const mockPost = vi.mocked(api.post);
      mockPost.mockClear();

      const store = useRatingStore.getState();

      // Set up pending ratings for session-123
      store.setPendingRatings("session-123", [
        {
          user_id: "user-1",
          username: "alice",
          display_name: "Alice",
          avatar_config: {},
        },
      ]);

      // Try to skip for different session
      await store.skipAll("session-456");

      // Should NOT call API
      expect(mockPost).not.toHaveBeenCalled();

      // Should set error
      expect(useRatingStore.getState().error).toBe(
        "Session mismatch: cannot rate a different session"
      );
    });
  });
});
