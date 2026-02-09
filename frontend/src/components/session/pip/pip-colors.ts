import type { SessionPhase } from "@/stores/session-store";
import type { PresenceState } from "@/types/activity";

/**
 * Hardcoded hex colors from globals.css design tokens.
 * PiP windows (both Document and Canvas) cannot read CSS variables
 * from the parent document, so we duplicate the values here.
 */

export const PHASE_BG_COLORS: Record<SessionPhase, string> = {
  idle: "#ede8e0",
  setup: "#ede8e0",
  work1: "#8b7355",
  break: "#7d9b76",
  work2: "#8b7355",
  social: "#d4a574",
  completed: "#ede8e0",
};

export const PHASE_TEXT_COLORS: Record<SessionPhase, string> = {
  idle: "#6b6560",
  setup: "#6b6560",
  work1: "#faf8f5",
  break: "#faf8f5",
  work2: "#faf8f5",
  social: "#3d3529",
  completed: "#6b6560",
};

export const PRESENCE_BORDER_COLORS: Record<PresenceState, string> = {
  active: "#7d9b76",
  grace: "#7d9b76",
  away: "#c9a962",
  ghosting: "#b85c5c",
};

export const PIP_BG_DARK = "#3d3529";
export const PIP_TEXT_LIGHT = "#faf8f5";
export const PIP_TEXT_DIM = "#a89e92";

export const PHASE_LABELS: Record<SessionPhase, string> = {
  idle: "Not Started",
  setup: "Setup",
  work1: "Work Block 1",
  break: "Break",
  work2: "Work Block 2",
  social: "Social Time",
  completed: "Completed",
};

export interface PiPParticipant {
  displayName: string | null;
  presenceState: PresenceState;
}
