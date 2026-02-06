"use client";

import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useUserStore, type UserProfile } from "@/stores/user-store";
import { useCreditsStore, type CreditTier } from "@/stores/credits-store";
import { api, ApiError } from "@/lib/api/client";
import { clearAuthToken } from "@/lib/auth-token";

/**
 * Hook for auth-related actions and state reading.
 *
 * NOTE: This hook does NOT set up auth state listeners.
 * Auth initialization is handled by AuthProvider at the layout level.
 * This hook only provides actions (signOut, refreshProfile) and state access.
 */
export function useAuth() {
  const router = useRouter();
  const { user, isLoading, error, setUser, setLoading, setError, clearUser } = useUserStore();
  const { setCredits, setTier, setRefreshDate } = useCreditsStore();

  const signOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    clearAuthToken();
    clearUser();
    router.push("/login");
  };

  const refreshProfile = async () => {
    setLoading(true);
    try {
      const profile = await api.get<UserProfile>("/users/me");
      setUser(profile);
      setCredits(profile.credits_remaining, profile.credits_used_this_week);
      setTier(profile.credit_tier as CreditTier);
      if (profile.credit_refresh_date) {
        setRefreshDate(profile.credit_refresh_date);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to refresh profile");
      }
    } finally {
      setLoading(false);
    }
  };

  return {
    user,
    isLoading,
    error,
    isAuthenticated: !!user,
    signOut,
    refreshProfile,
  };
}
