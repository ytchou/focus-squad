"use client";

import { useEffect, useRef } from "react";
import { createClient } from "@/lib/supabase/client";
import { useUserStore, type UserProfile } from "@/stores/user-store";
import { useCreditsStore, type CreditTier } from "@/stores/credits-store";
import { api, ApiError } from "@/lib/api/client";
import { setAuthToken, clearAuthToken } from "@/lib/auth-token";

/**
 * AuthProvider initializes auth state and syncs user/credits on app load.
 * Must wrap all protected routes.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const initialized = useRef(false);

  useEffect(() => {
    // Prevent double initialization in React StrictMode
    if (initialized.current) return;
    initialized.current = true;

    const supabase = createClient();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      if ((event === "SIGNED_IN" || event === "INITIAL_SESSION") && session) {
        setAuthToken(session.access_token);
        useUserStore.getState().setLoading(true);

        try {
          const profile = await api.get<UserProfile>("/users/me");

          // Onboarding gate: redirect un-onboarded users to the wizard
          if (!profile.is_onboarded) {
            useUserStore.getState().setUser(profile);
            useUserStore.getState().setLoading(false);
            if (
              typeof window !== "undefined" &&
              !window.location.pathname.startsWith("/onboarding")
            ) {
              window.location.href = "/onboarding";
            }
            return;
          }

          useUserStore.getState().setUser(profile);
          useCreditsStore
            .getState()
            .setCredits(profile.credits_remaining, profile.credits_used_this_week);
          useCreditsStore.getState().setTier(profile.credit_tier as CreditTier);
          if (profile.credit_refresh_date) {
            useCreditsStore.getState().setRefreshDate(profile.credit_refresh_date);
          }
        } catch (err) {
          if (err instanceof ApiError) {
            useUserStore.getState().setError(err.message);
          } else {
            useUserStore.getState().setError("Failed to load profile");
          }
        } finally {
          useUserStore.getState().setLoading(false);
        }
      } else if (event === "SIGNED_OUT") {
        clearAuthToken();
        useUserStore.getState().clearUser();
      }
    });

    return () => subscription.unsubscribe();
  }, []); // Empty deps - runs once, uses store.getState() for stability

  return <>{children}</>;
}
