"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { PresenceState } from "@/types/activity";

const GRACE_TIMEOUT = 2 * 60 * 1000;
const AWAY_TIMEOUT = 5 * 60 * 1000;
const TICK_INTERVAL = 10 * 1000;
const TYPING_TIMEOUT = 3 * 1000;

export interface UsePresenceDetectionOptions {
  enabled: boolean;
  inputTrackingConsent: boolean;
  isPiPActive?: boolean;
  onStateChange?: (state: PresenceState, prev: PresenceState) => void;
}

export interface UsePresenceDetectionReturn {
  presenceState: PresenceState;
  isPageVisible: boolean;
  isTyping: boolean;
}

function deriveState(isPageVisible: boolean, elapsed: number): PresenceState {
  if (isPageVisible && elapsed < GRACE_TIMEOUT) return "active";
  if (!isPageVisible && elapsed < GRACE_TIMEOUT) return "grace";
  if (elapsed < AWAY_TIMEOUT) return "away";
  return "ghosting";
}

export function usePresenceDetection({
  enabled,
  inputTrackingConsent,
  isPiPActive,
  onStateChange,
}: UsePresenceDetectionOptions): UsePresenceDetectionReturn {
  const [isPageVisible, setIsPageVisible] = useState(true);
  const [presenceState, setPresenceState] = useState<PresenceState>("active");
  const [isTyping, setIsTyping] = useState(false);

  const lastSignalAt = useRef(0);
  const prevStateRef = useRef<PresenceState>("active");
  const onStateChangeRef = useRef(onStateChange);
  const isPiPActiveRef = useRef(isPiPActive ?? false);
  const typingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    onStateChangeRef.current = onStateChange;
  }, [onStateChange]);

  useEffect(() => {
    isPiPActiveRef.current = isPiPActive ?? false;
  }, [isPiPActive]);

  const recordSignal = useCallback(() => {
    lastSignalAt.current = Date.now();
  }, []);

  useEffect(() => {
    if (!enabled) {
      // No cleanup needed; the hook returns hardcoded values when disabled
      prevStateRef.current = "active";
      return;
    }

    // Initialize signal timestamp on mount
    lastSignalAt.current = Date.now();

    const handleVisibilityChange = () => {
      const visible = document.visibilityState === "visible" || isPiPActiveRef.current;
      setIsPageVisible(visible);
      if (visible) {
        recordSignal();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    const inputListeners: Array<[string, EventListener]> = [];

    if (inputTrackingConsent) {
      const handleInput = () => recordSignal();
      const handleKeydown = () => {
        recordSignal();
        setIsTyping(true);
        if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
        typingTimerRef.current = setTimeout(() => setIsTyping(false), TYPING_TIMEOUT);
      };

      window.addEventListener("keydown", handleKeydown, { passive: true });
      inputListeners.push(["keydown", handleKeydown]);

      const otherEvents = ["mousedown", "mousemove", "touchstart"];
      for (const event of otherEvents) {
        window.addEventListener(event, handleInput, { passive: true });
        inputListeners.push([event, handleInput]);
      }
    }

    const interval = setInterval(() => {
      const elapsed = Date.now() - lastSignalAt.current;
      const visible = document.visibilityState === "visible" || isPiPActiveRef.current;
      const next = deriveState(visible, elapsed);

      setPresenceState(next);

      if (next !== prevStateRef.current) {
        onStateChangeRef.current?.(next, prevStateRef.current);
        prevStateRef.current = next;
      }
    }, TICK_INTERVAL);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      for (const [event, handler] of inputListeners) {
        window.removeEventListener(event, handler);
      }
      clearInterval(interval);
      if (typingTimerRef.current) {
        clearTimeout(typingTimerRef.current);
        typingTimerRef.current = null;
      }
      setIsTyping(false);
    };
  }, [enabled, inputTrackingConsent, recordSignal]);

  if (!enabled) {
    return { presenceState: "active", isPageVisible: true, isTyping: false };
  }

  return { presenceState, isPageVisible, isTyping };
}
