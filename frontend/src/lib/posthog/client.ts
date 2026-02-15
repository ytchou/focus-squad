import posthog from "posthog-js";

export const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY ?? "";
export const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://us.i.posthog.com";

let initialized = false;

export function initPostHog(): typeof posthog {
  if (typeof window === "undefined") return posthog;
  if (initialized) return posthog;
  if (!POSTHOG_KEY) {
    console.warn("[PostHog] No API key configured — analytics disabled");
    return posthog;
  }

  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    capture_pageview: false,
    capture_pageleave: true,
    autocapture: true,
    persistence: "localStorage+cookie",
    loaded: (_ph) => {
      if (process.env.NODE_ENV === "development") {
        console.log("[PostHog] Initialized in development mode");
      }
    },
  });

  initialized = true;
  return posthog;
}

export function getPostHog(): typeof posthog {
  return posthog;
}
