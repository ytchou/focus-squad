"use client";

import { useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import posthog from "posthog-js";
import { initPostHog, POSTHOG_KEY } from "@/lib/posthog/client";
import { useSessionStore } from "@/stores/session-store";
import { trackTabFocusChanged } from "@/lib/posthog/events";

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    initPostHog();
  }, []);

  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (!POSTHOG_KEY) return;
    if (!posthog.__loaded) return;

    const url = window.origin + pathname + (searchParams?.toString() ? `?${searchParams.toString()}` : "");
    posthog.capture("$pageview", { $current_url: url });
  }, [pathname, searchParams]);

  // Track tab focus/blur for session engagement analysis
  useEffect(() => {
    const handleVisibilityChange = () => {
      const visible = document.visibilityState === "visible";
      const sessionId = useSessionStore.getState().sessionId;
      trackTabFocusChanged(visible, sessionId ?? undefined);
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  return <>{children}</>;
}
