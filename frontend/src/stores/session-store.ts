import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Session phases match the 55-minute structure from SPEC.md:
 * idle -> setup (3min) -> work1 (25min) -> break (2min) -> work2 (20min) -> social (5min) -> completed
 */
export type SessionPhase = "idle" | "setup" | "work1" | "break" | "work2" | "social" | "completed";

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

  // Waiting room state
  sessionStartTime: Date | null; // Absolute UTC start time
  waitMinutes: number | null; // From API response
  isWaiting: boolean; // True when in waiting room
  isImmediate: boolean; // True if <1 min until start

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
  setWaitingRoom: (startTime: Date, waitMinutes: number, isImmediate: boolean) => void;
  clearWaitingRoom: () => void;
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
  sessionStartTime: null,
  waitMinutes: null,
  isWaiting: false,
  isImmediate: false,
};

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
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

  setWaitingRoom: (startTime, waitMinutes, isImmediate) =>
    set({
      sessionStartTime: startTime,
      waitMinutes,
      isWaiting: true,
      isImmediate,
    }),

  clearWaitingRoom: () =>
    set({
      sessionStartTime: null,
      waitMinutes: null,
      isWaiting: false,
      isImmediate: false,
    }),

  leaveSession: () =>
    set({
      ...initialState,
      currentPhase: "idle",
    }),

  reset: () => set(initialState),
    }),
    {
      name: "focus-squad-session",
      partialize: (state) => ({
        sessionId: state.sessionId,
        sessionStartTime: state.sessionStartTime,
        isWaiting: state.isWaiting,
        waitMinutes: state.waitMinutes,
        isImmediate: state.isImmediate,
      }),
    }
  )
);
