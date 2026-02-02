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
  reliability_score: number;
  total_focus_minutes: number;
  session_count: number;
  current_streak: number;
  language: string;
  created_at: string;
  updated_at: string;
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
