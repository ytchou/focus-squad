import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface UserProfile {
  id: string;
  auth_id: string;
  email: string;
  username: string;
  display_name: string | null;
  bio: string | null;
  avatar_config: Record<string, unknown>;
  pixel_avatar_id: string | null;
  // Onboarding & preferences
  is_onboarded: boolean;
  default_table_mode: "forced_audio" | "quiet";
  // Stats
  reliability_score: number;
  total_focus_minutes: number;
  session_count: number;
  current_streak: number;
  longest_streak: number;
  last_session_date: string | null;
  preferred_language: string;
  // Settings
  activity_tracking_enabled: boolean;
  email_notifications_enabled: boolean;
  push_notifications_enabled: boolean;
  // Timestamps
  created_at: string;
  updated_at: string;
  banned_until: string | null;
  deleted_at: string | null;
  // Credit info (joined from credits table)
  credits_remaining: number;
  credits_used_this_week: number;
  credit_tier: "free" | "pro" | "elite" | "infinite";
  credit_refresh_date: string | null;
}

interface UserState {
  user: UserProfile | null;
  isLoading: boolean;
  error: string | null;

  setUser: (user: UserProfile | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearUser: () => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set) => ({
      user: null,
      isLoading: false,
      error: null,

      setUser: (user) => set({ user, isLoading: false, error: null }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error, isLoading: false }),
      clearUser: () => set({ user: null, isLoading: false, error: null }),
    }),
    {
      name: "focus-squad-user",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ user: state.user }),
    }
  )
);
