import { create } from "zustand";
import { api } from "@/lib/api/client";

// =============================================================================
// Types
// =============================================================================

export interface WeeklyStreakResponse {
  session_count: number;
  week_start: string;
  next_bonus_at: number;
  bonus_3_awarded: boolean;
  bonus_5_awarded: boolean;
  total_bonus_earned: number;
}

export interface MoodResponse {
  mood: "positive" | "neutral" | "tired";
  score: number;
  positive_count: number;
  negative_count: number;
  total_count: number;
}

export interface CompanionReactionResponse {
  companion_type: string;
  animation: string;
  tag: string;
}

export interface RoomSnapshot {
  id: string;
  milestone_type: string;
  image_url: string;
  session_count_at: number;
  diary_excerpt: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface TimelineResponse {
  snapshots: RoomSnapshot[];
  total: number;
  page: number;
  per_page: number;
}

export interface SnapshotUploadRequest {
  milestone_type: string;
  image_base64: string;
  diary_excerpt?: string;
  metadata?: Record<string, unknown>;
}

export interface SnapshotUploadResponse {
  id: string;
  image_url: string;
  milestone_type: string;
  created_at: string;
}

// =============================================================================
// Store
// =============================================================================

interface GamificationState {
  weeklyStreak: WeeklyStreakResponse | null;
  mood: MoodResponse | null;
  pendingReaction: CompanionReactionResponse | null;
  snapshots: RoomSnapshot[];
  timelineTotal: number;
  timelinePage: number;
  pendingMilestones: string[];
  isLoading: boolean;
  isTimelineLoading: boolean;
  error: string | null;

  fetchStreak: () => Promise<void>;
  fetchMood: () => Promise<void>;
  setPendingReaction: (reaction: CompanionReactionResponse | null) => void;
  clearPendingReaction: () => void;
  fetchTimeline: (page?: number) => Promise<void>;
  checkMilestones: () => Promise<string[]>;
  uploadSnapshot: (req: SnapshotUploadRequest) => Promise<SnapshotUploadResponse | null>;
  reset: () => void;
}

const initialState = {
  weeklyStreak: null as WeeklyStreakResponse | null,
  mood: null as MoodResponse | null,
  pendingReaction: null as CompanionReactionResponse | null,
  snapshots: [] as RoomSnapshot[],
  timelineTotal: 0,
  timelinePage: 1,
  pendingMilestones: [] as string[],
  isLoading: false,
  isTimelineLoading: false,
  error: null as string | null,
};

export const useGamificationStore = create<GamificationState>()((set, get) => ({
  ...initialState,

  fetchStreak: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.get<WeeklyStreakResponse>("/api/v1/gamification/streak");
      set({ weeklyStreak: data, isLoading: false });
    } catch {
      set({ error: "Failed to load streak", isLoading: false });
    }
  },

  fetchMood: async () => {
    try {
      const data = await api.get<MoodResponse>("/api/v1/gamification/mood");
      set({ mood: data });
    } catch {
      // Mood fetch is non-critical, silently fail
    }
  },

  setPendingReaction: (reaction) => set({ pendingReaction: reaction }),

  clearPendingReaction: () => set({ pendingReaction: null }),

  fetchTimeline: async (page = 1) => {
    set({ isTimelineLoading: true });
    try {
      const data = await api.get<TimelineResponse>(
        `/api/v1/gamification/timeline?page=${page}&per_page=10`
      );
      if (page === 1) {
        set({
          snapshots: data.snapshots,
          timelineTotal: data.total,
          timelinePage: page,
          isTimelineLoading: false,
        });
      } else {
        set({
          snapshots: [...get().snapshots, ...data.snapshots],
          timelineTotal: data.total,
          timelinePage: page,
          isTimelineLoading: false,
        });
      }
    } catch {
      set({ isTimelineLoading: false });
    }
  },

  checkMilestones: async () => {
    try {
      const milestones = await api.get<string[]>("/api/v1/gamification/timeline/milestones");
      set({ pendingMilestones: milestones });
      return milestones;
    } catch {
      return [];
    }
  },

  uploadSnapshot: async (req) => {
    try {
      const data = await api.post<SnapshotUploadResponse>(
        "/api/v1/gamification/timeline/snapshot",
        req
      );
      // Prepend to local snapshots list
      const snapshot: RoomSnapshot = {
        id: data.id,
        milestone_type: data.milestone_type,
        image_url: data.image_url,
        session_count_at: 0,
        diary_excerpt: req.diary_excerpt ?? null,
        metadata: req.metadata ?? {},
        created_at: data.created_at,
      };
      set((state) => ({
        snapshots: [snapshot, ...state.snapshots],
        timelineTotal: state.timelineTotal + 1,
        pendingMilestones: state.pendingMilestones.filter((m) => m !== req.milestone_type),
      }));
      return data;
    } catch {
      return null;
    }
  },

  reset: () => set(initialState),
}));
