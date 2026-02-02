import { create } from "zustand";

/**
 * Session phases match the 55-minute structure from SPEC.md:
 * idle -> setup (3min) -> work1 (25min) -> break (2min) -> work2 (20min) -> social (5min) -> completed
 */
export type SessionPhase =
  | "idle"
  | "setup"
  | "work1"
  | "break"
  | "work2"
  | "social"
  | "completed";

export interface Participant {
  id: string;
  username: string;
  displayName: string | null;
  avatarConfig: Record<string, unknown>;
  isAI: boolean;
  isMuted: boolean;
  isActive: boolean;
}

interface SessionState {
  // Session info
  sessionId: string | null;
  tableId: string | null;
  currentPhase: SessionPhase;
  timeRemaining: number; // seconds

  // Participants (max 4 per table)
  participants: Participant[];

  // Matching state
  isMatching: boolean;
  matchingStartedAt: Date | null;

  // Audio state
  isMuted: boolean;
  isQuietMode: boolean;

  // Actions
  setSession: (sessionId: string, tableId: string, participants: Participant[]) => void;
  setPhase: (phase: SessionPhase) => void;
  setTimeRemaining: (time: number) => void;
  decrementTime: () => void;
  updateParticipant: (participantId: string, updates: Partial<Participant>) => void;
  removeParticipant: (participantId: string) => void;
  addParticipant: (participant: Participant) => void;
  setMatching: (isMatching: boolean) => void;
  setMuted: (isMuted: boolean) => void;
  setQuietMode: (isQuietMode: boolean) => void;
  leaveSession: () => void;
  reset: () => void;
}

const initialState = {
  sessionId: null,
  tableId: null,
  currentPhase: "idle" as SessionPhase,
  timeRemaining: 0,
  participants: [],
  isMatching: false,
  matchingStartedAt: null,
  isMuted: false,
  isQuietMode: false,
};

export const useSessionStore = create<SessionState>((set, get) => ({
  ...initialState,

  setSession: (sessionId, tableId, participants) =>
    set({
      sessionId,
      tableId,
      participants,
      currentPhase: "setup",
      isMatching: false,
      matchingStartedAt: null,
    }),

  setPhase: (phase) => set({ currentPhase: phase }),

  setTimeRemaining: (time) => set({ timeRemaining: time }),

  decrementTime: () => {
    const { timeRemaining } = get();
    if (timeRemaining > 0) {
      set({ timeRemaining: timeRemaining - 1 });
    }
  },

  updateParticipant: (participantId, updates) =>
    set((state) => ({
      participants: state.participants.map((p) =>
        p.id === participantId ? { ...p, ...updates } : p
      ),
    })),

  removeParticipant: (participantId) =>
    set((state) => ({
      participants: state.participants.filter((p) => p.id !== participantId),
    })),

  addParticipant: (participant) =>
    set((state) => ({
      participants: [...state.participants, participant],
    })),

  setMatching: (isMatching) =>
    set({
      isMatching,
      matchingStartedAt: isMatching ? new Date() : null,
    }),

  setMuted: (isMuted) => set({ isMuted }),

  setQuietMode: (isQuietMode) => set({ isQuietMode }),

  leaveSession: () =>
    set({
      ...initialState,
      currentPhase: "idle",
    }),

  reset: () => set(initialState),
}));
