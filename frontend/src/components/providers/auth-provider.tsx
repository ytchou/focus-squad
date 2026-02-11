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
            if (profile.preferred_language) {
              document.cookie = `NEXT_LOCALE=${profile.preferred_language};path=/;max-age=31536000;SameSite=Lax`;
            }
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

          // Auto-cancel pending deletion when user signs back in
          let activeProfile = profile;
          if (profile.deleted_at) {
            try {
              activeProfile = await api.post<UserProfile>("/users/me/cancel-deletion");
            } catch {
              // Non-critical: proceed with stale profile
            }
          }

          // Set locale cookie for next-intl SSR
          if (activeProfile.preferred_language) {
            document.cookie = `NEXT_LOCALE=${activeProfile.preferred_language};path=/;max-age=31536000;SameSite=Lax`;
          }

          useUserStore.getState().setUser(activeProfile);
          useCreditsStore
            .getState()
            .setCredits(activeProfile.credits_remaining, activeProfile.credits_used_this_week);
          useCreditsStore.getState().setTier(activeProfile.credit_tier as CreditTier);
          if (activeProfile.credit_refresh_date) {
            useCreditsStore.getState().setRefreshDate(activeProfile.credit_refresh_date);
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
        document.cookie = "NEXT_LOCALE=;path=/;max-age=0";
        useUserStore.getState().clearUser();
      }
    });

    return () => subscription.unsubscribe();
  }, []); // Empty deps - runs once, uses store.getState() for stability

  return <>{children}</>;
}
