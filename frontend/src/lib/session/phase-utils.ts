import type { SessionPhase } from "@/stores/session-store";

/**
 * Session phase boundaries in minutes.
 * Total duration: 55 minutes
 *
 * Timeline:
 * - 0-3 min: Setup (trickle-in, doesn't count for rewards)
 * - 3-28 min: Work Block 1 (25 min focus)
 * - 28-30 min: Break (2 min rest)
 * - 30-50 min: Work Block 2 (20 min focus)
 * - 50-55 min: Social (chat, peer review)
 */
export const PHASE_BOUNDARIES: Record<
  Exclude<SessionPhase, "idle" | "completed">,
  { start: number; end: number; label: string }
> = {
  setup: { start: 0, end: 3, label: "Setup" },
  work1: { start: 3, end: 28, label: "Work Block 1" },
  break: { start: 28, end: 30, label: "Break" },
  work2: { start: 30, end: 50, label: "Work Block 2" },
  social: { start: 50, end: 55, label: "Social" },
};

export const SESSION_DURATION_MINUTES = 55;
export const SESSION_DURATION_SECONDS = SESSION_DURATION_MINUTES * 60;

/**
 * Phase colors using design system tokens.
 * Used for phase badges and visual indicators.
 */
export const PHASE_COLORS: Record<SessionPhase, string> = {
  idle: "bg-muted text-muted-foreground",
  setup: "bg-muted text-muted-foreground",
  work1: "bg-primary text-primary-foreground",
  break: "bg-success text-success-foreground",
  work2: "bg-primary text-primary-foreground",
  social: "bg-accent text-accent-foreground",
  completed: "bg-muted text-muted-foreground",
};

/**
 * Phase display labels for UI.
 */
export const PHASE_LABELS: Record<SessionPhase, string> = {
  idle: "Not Started",
  setup: "Setup",
  work1: "Work Block 1",
  break: "Break",
  work2: "Work Block 2",
  social: "Social Time",
  completed: "Completed",
};

export interface PhaseInfo {
  phase: SessionPhase;
  timeRemaining: number; // seconds remaining in current phase
  totalTimeRemaining: number; // seconds remaining in entire session
  progress: number; // 0-1 progress through current phase
  elapsedMinutes: number;
}

/**
 * Calculate current phase and timing based on session start time.
 * This calculation should match the backend logic in session_service.py.
 *
 * @param sessionStartTime - The UTC start time of the session
 * @param now - Current time (optional, defaults to Date.now())
 * @returns PhaseInfo with current phase and timing details
 */
export function calculatePhaseInfo(
  sessionStartTime: Date | string,
  now: Date = new Date()
): PhaseInfo {
  const startTime =
    typeof sessionStartTime === "string" ? new Date(sessionStartTime) : sessionStartTime;

  const elapsedMs = now.getTime() - startTime.getTime();
  const elapsedMinutes = elapsedMs / 60000;
  const elapsedSeconds = elapsedMs / 1000;

  // Session hasn't started yet
  if (elapsedMinutes < 0) {
    return {
      phase: "idle",
      timeRemaining: Math.abs(elapsedSeconds),
      totalTimeRemaining: SESSION_DURATION_SECONDS + Math.abs(elapsedSeconds),
      progress: 0,
      elapsedMinutes: 0,
    };
  }

  // Session has ended
  if (elapsedMinutes >= SESSION_DURATION_MINUTES) {
    return {
      phase: "completed",
      timeRemaining: 0,
      totalTimeRemaining: 0,
      progress: 1,
      elapsedMinutes: SESSION_DURATION_MINUTES,
    };
  }

  // Find current phase
  for (const [phase, bounds] of Object.entries(PHASE_BOUNDARIES)) {
    if (elapsedMinutes >= bounds.start && elapsedMinutes < bounds.end) {
      const phaseDurationMinutes = bounds.end - bounds.start;
      const minutesIntoPhase = elapsedMinutes - bounds.start;
      const timeRemainingInPhase = (bounds.end - elapsedMinutes) * 60;
      const totalTimeRemaining = (SESSION_DURATION_MINUTES - elapsedMinutes) * 60;

      return {
        phase: phase as SessionPhase,
        timeRemaining: Math.max(0, Math.floor(timeRemainingInPhase)),
        totalTimeRemaining: Math.max(0, Math.floor(totalTimeRemaining)),
        progress: minutesIntoPhase / phaseDurationMinutes,
        elapsedMinutes,
      };
    }
  }

  // Fallback (shouldn't reach here)
  return {
    phase: "completed",
    timeRemaining: 0,
    totalTimeRemaining: 0,
    progress: 1,
    elapsedMinutes: SESSION_DURATION_MINUTES,
  };
}

/**
 * Format seconds as MM:SS string.
 * Matches the formatTime function in waiting room page.
 */
export function formatTime(seconds: number): string {
  const mins = Math.floor(Math.max(0, seconds) / 60);
  const secs = Math.floor(Math.max(0, seconds) % 60);
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
}

/**
 * Get the next phase after the current one.
 */
export function getNextPhase(currentPhase: SessionPhase): SessionPhase | null {
  const phaseOrder: SessionPhase[] = [
    "idle",
    "setup",
    "work1",
    "break",
    "work2",
    "social",
    "completed",
  ];
  const currentIndex = phaseOrder.indexOf(currentPhase);

  if (currentIndex === -1 || currentIndex >= phaseOrder.length - 1) {
    return null;
  }

  return phaseOrder[currentIndex + 1];
}

/**
 * Check if the current phase is a work phase (for UI emphasis).
 */
export function isWorkPhase(phase: SessionPhase): boolean {
  return phase === "work1" || phase === "work2";
}

/**
 * Get duration of a specific phase in seconds.
 */
export function getPhaseDuration(phase: SessionPhase): number {
  if (phase === "idle" || phase === "completed") {
    return 0;
  }

  const bounds = PHASE_BOUNDARIES[phase];
  return (bounds.end - bounds.start) * 60;
}
