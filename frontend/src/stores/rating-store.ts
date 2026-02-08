import { create } from "zustand";
import { api } from "@/lib/api/client";

export type RatingValue = "green" | "red" | "skip" | null;

export interface RateableUser {
  user_id: string;
  username: string;
  display_name: string | null;
  avatar_config: Record<string, unknown>;
}

export interface RatingEntry {
  value: RatingValue;
  reasons: string[];
  otherReasonText: string;
}

export interface RatingHistorySummary {
  total_received: number;
  green_count: number;
  red_count: number;
  green_percentage: number;
}

export interface RatingHistoryItem {
  id: string;
  session_id: string;
  rating: "green" | "red";
  created_at: string;
}

export interface RatingHistoryData {
  summary: RatingHistorySummary;
  items: RatingHistoryItem[];
  total: number;
  page: number;
  per_page: number;
}

interface RatingState {
  hasPendingRatings: boolean;
  pendingSessionId: string | null;
  rateableUsers: RateableUser[];
  ratings: Record<string, RatingEntry>;
  isSubmitting: boolean;
  error: string | null;
  ratingHistory: RatingHistoryData | null;
  isLoadingHistory: boolean;

  setRating: (userId: string, value: RatingValue) => void;
  setReasons: (userId: string, reasons: string[]) => void;
  setOtherText: (userId: string, text: string) => void;
  submitRatings: (sessionId: string) => Promise<void>;
  skipAll: (sessionId: string) => Promise<void>;
  checkPendingRatings: () => Promise<void>;
  setPendingRatings: (sessionId: string, users: RateableUser[]) => void;
  fetchRatingHistory: (page?: number) => Promise<void>;
  reset: () => void;
}

const initialState = {
  hasPendingRatings: false,
  pendingSessionId: null,
  rateableUsers: [],
  ratings: {} as Record<string, RatingEntry>,
  isSubmitting: false,
  error: null,
  ratingHistory: null as RatingHistoryData | null,
  isLoadingHistory: false,
};

export const useRatingStore = create<RatingState>()((set, get) => ({
  ...initialState,

  setPendingRatings: (sessionId, users) => {
    const ratings: Record<string, RatingEntry> = {};
    for (const user of users) {
      ratings[user.user_id] = {
        value: null,
        reasons: [],
        otherReasonText: "",
      };
    }
    set({
      hasPendingRatings: true,
      pendingSessionId: sessionId,
      rateableUsers: users,
      ratings,
      error: null,
    });
  },

  setRating: (userId, value) =>
    set((state) => ({
      ratings: {
        ...state.ratings,
        [userId]: {
          ...state.ratings[userId],
          value,
          // Clear reasons when switching away from red
          reasons: value === "red" ? (state.ratings[userId]?.reasons ?? []) : [],
          otherReasonText: value === "red" ? (state.ratings[userId]?.otherReasonText ?? "") : "",
        },
      },
    })),

  setReasons: (userId, reasons) =>
    set((state) => ({
      ratings: {
        ...state.ratings,
        [userId]: {
          ...state.ratings[userId],
          reasons,
          // Clear other text if "other" reason was deselected
          otherReasonText: reasons.includes("other")
            ? (state.ratings[userId]?.otherReasonText ?? "")
            : "",
        },
      },
    })),

  setOtherText: (userId, text) =>
    set((state) => ({
      ratings: {
        ...state.ratings,
        [userId]: {
          ...state.ratings[userId],
          otherReasonText: text,
        },
      },
    })),

  submitRatings: async (sessionId) => {
    const { ratings } = get();
    set({ isSubmitting: true, error: null });

    try {
      const ratingsPayload = Object.entries(ratings)
        .filter(([, entry]) => entry.value !== null)
        .map(([rateeId, entry]) => ({
          ratee_id: rateeId,
          rating: entry.value as "green" | "red" | "skip",
          ...(entry.value === "red" && entry.reasons.length > 0 ? { reasons: entry.reasons } : {}),
          ...(entry.value === "red" &&
          entry.reasons.includes("other") &&
          entry.otherReasonText.trim()
            ? { other_reason_text: entry.otherReasonText.trim() }
            : {}),
        }));

      await api.post(`/api/v1/sessions/${sessionId}/rate`, {
        ratings: ratingsPayload,
      });

      set({
        ...initialState,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to submit ratings";
      set({ error: message, isSubmitting: false });
    }
  },

  skipAll: async (sessionId) => {
    set({ isSubmitting: true, error: null });

    try {
      await api.post(`/api/v1/sessions/${sessionId}/rate/skip`);

      set({
        ...initialState,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to skip ratings";
      set({ error: message, isSubmitting: false });
    }
  },

  checkPendingRatings: async () => {
    try {
      const data = await api.get<{
        has_pending: boolean;
        pending: {
          session_id: string;
          rateable_users: RateableUser[];
          expires_at: string;
        } | null;
      }>("/api/v1/sessions/pending-ratings");

      if (data.has_pending && data.pending && data.pending.rateable_users.length > 0) {
        get().setPendingRatings(data.pending.session_id, data.pending.rateable_users);
      } else {
        set({ hasPendingRatings: false, pendingSessionId: null });
      }
    } catch {
      // Silently fail - pending ratings check is non-critical
    }
  },

  fetchRatingHistory: async (page = 1) => {
    set({ isLoadingHistory: true });
    try {
      const data = await api.get<RatingHistoryData>(
        `/api/v1/sessions/rating-history?page=${page}&per_page=20`
      );
      set({ ratingHistory: data, isLoadingHistory: false });
    } catch {
      set({ isLoadingHistory: false });
    }
  },

  reset: () => set(initialState),
}));
