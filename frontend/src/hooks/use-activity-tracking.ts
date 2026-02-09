"use client";

import { useState, useEffect, useCallback, useRef } from "react";

const ACTIVITY_TIMEOUT_MS = 30 * 1000; // 30 seconds of inactivity = idle

interface UseActivityTrackingOptions {
  enabled: boolean;
  onActivityChange?: (isActive: boolean) => void;
}

interface UseActivityTrackingReturn {
  isActive: boolean;
  lastActivityAt: Date | null;
}

/**
 * @deprecated Use `usePresenceDetection` from `@/hooks/use-presence-detection` instead.
 * This hook has a simple 30s timeout and no page visibility awareness.
 * The new hook provides a 4-state presence machine (active/grace/away/ghosting)
 * with proper Page Visibility API integration and opt-in input tracking.
 *
 * @param options - Configuration options
 * @returns Activity state
 */
export function useActivityTracking({
  enabled,
  onActivityChange,
}: UseActivityTrackingOptions): UseActivityTrackingReturn {
  const [isActive, setIsActive] = useState(false);
  const [lastActivityAt, setLastActivityAt] = useState<Date | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const previousActiveRef = useRef(false);

  const handleActivity = useCallback(() => {
    if (!enabled) return;

    const now = new Date();
    setLastActivityAt(now);
    setIsActive(true);

    // Clear existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Set new timeout to mark as idle
    timeoutRef.current = setTimeout(() => {
      setIsActive(false);
    }, ACTIVITY_TIMEOUT_MS);
  }, [enabled]);

  // Track activity state changes
  useEffect(() => {
    if (isActive !== previousActiveRef.current) {
      onActivityChange?.(isActive);
      previousActiveRef.current = isActive;
    }
  }, [isActive, onActivityChange]);

  // Set up event listeners
  useEffect(() => {
    if (!enabled) {
      return;
    }

    // Listen for keyboard and mouse events
    const events = ["keydown", "mousedown", "mousemove", "touchstart"];

    for (const event of events) {
      window.addEventListener(event, handleActivity, { passive: true });
    }

    return () => {
      for (const event of events) {
        window.removeEventListener(event, handleActivity);
      }

      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [enabled, handleActivity]);

  // Return false/null when disabled to avoid need for state reset
  return {
    isActive: enabled ? isActive : false,
    lastActivityAt: enabled ? lastActivityAt : null,
  };
}
