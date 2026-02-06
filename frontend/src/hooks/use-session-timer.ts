"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { SessionPhase } from "@/stores/session-store";
import { calculatePhaseInfo, type PhaseInfo } from "@/lib/session/phase-utils";

interface UseSessionTimerOptions {
  sessionStartTime: Date | string | null;
  onPhaseChange?: (newPhase: SessionPhase, previousPhase: SessionPhase) => void;
}

interface UseSessionTimerReturn extends PhaseInfo {
  isRunning: boolean;
}

/**
 * Hook that manages the session timer countdown.
 * Calculates current phase based on session start time.
 * Triggers onPhaseChange callback when phase transitions occur.
 *
 * @param options - Configuration options
 * @returns Current phase info and timer state
 */
export function useSessionTimer({
  sessionStartTime,
  onPhaseChange,
}: UseSessionTimerOptions): UseSessionTimerReturn {
  const [phaseInfo, setPhaseInfo] = useState<PhaseInfo>(() => {
    if (!sessionStartTime) {
      return {
        phase: "idle",
        timeRemaining: 0,
        totalTimeRemaining: 0,
        progress: 0,
        elapsedMinutes: 0,
      };
    }
    return calculatePhaseInfo(sessionStartTime);
  });

  const previousPhaseRef = useRef<SessionPhase>(phaseInfo.phase);
  const isRunning = sessionStartTime !== null && phaseInfo.phase !== "completed";

  const updateTimer = useCallback(() => {
    if (!sessionStartTime) return;

    const newPhaseInfo = calculatePhaseInfo(sessionStartTime);
    setPhaseInfo(newPhaseInfo);

    // Check for phase transition
    if (newPhaseInfo.phase !== previousPhaseRef.current) {
      onPhaseChange?.(newPhaseInfo.phase, previousPhaseRef.current);
      previousPhaseRef.current = newPhaseInfo.phase;
    }
  }, [sessionStartTime, onPhaseChange]);

  useEffect(() => {
    if (!sessionStartTime) {
      return;
    }

    // Initial state is already calculated in useState initializer.
    // The interval handles all subsequent updates, starting immediately.
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [sessionStartTime, updateTimer]);

  return {
    ...phaseInfo,
    isRunning,
  };
}
