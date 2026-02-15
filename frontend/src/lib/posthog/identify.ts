import posthog from "posthog-js";
import type { UserProfile } from "@/stores/user-store";

export function identifyUser(profile: UserProfile): void {
  if (!posthog.__loaded) return;

  posthog.identify(profile.id, {
    email: profile.email,
    username: profile.username,
    display_name: profile.display_name,
    tier: profile.credit_tier,
    is_paid: profile.credit_tier !== "free",
    reliability_score: profile.reliability_score,
    total_sessions: profile.session_count,
    weekly_streak: profile.current_streak,
    onboarded: profile.is_onboarded,
    preferred_mode: profile.default_table_mode,
    locale: profile.preferred_language,
    created_at: profile.created_at,
  });
}

export function resetUser(): void {
  if (!posthog.__loaded) return;
  posthog.reset();
}

export function setUserOptOut(optOut: boolean): void {
  if (!posthog.__loaded) return;
  if (optOut) {
    posthog.opt_out_capturing();
  } else {
    posthog.opt_in_capturing();
  }
}
