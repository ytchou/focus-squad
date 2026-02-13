import { describe, it, expect, beforeEach } from "vitest";
import { useSessionStore, type Participant } from "../session-store";

describe("Session Store", () => {
  const mockParticipant: Participant = {
    id: "user-1",
    username: "testuser",
    displayName: "Test User",
    avatarConfig: {},
    isAI: false,
    isMuted: false,
    isActive: true,
  };

  beforeEach(() => {
    // Reset store to initial state
    useSessionStore.getState().reset();
  });

  describe("setSession", () => {
    it("should set session with participants and transition to setup phase", () => {
      const store = useSessionStore.getState();
      store.setSession("session-123", "table-456", [mockParticipant]);

      const state = useSessionStore.getState();
      expect(state.sessionId).toBe("session-123");
      expect(state.tableId).toBe("table-456");
      expect(state.participants).toHaveLength(1);
      expect(state.currentPhase).toBe("setup");
      expect(state.isMatching).toBe(false);
    });
  });

  describe("setPhase", () => {
    it("should update current phase", () => {
      const store = useSessionStore.getState();
      store.setPhase("work1");

      expect(useSessionStore.getState().currentPhase).toBe("work1");
    });

    it("should cycle through all phases", () => {
      const store = useSessionStore.getState();
      const phases = ["setup", "work1", "break", "work2", "social", "completed"] as const;

      for (const phase of phases) {
        store.setPhase(phase);
        expect(useSessionStore.getState().currentPhase).toBe(phase);
      }
    });
  });

  describe("timeRemaining", () => {
    it("should set time remaining", () => {
      const store = useSessionStore.getState();
      store.setTimeRemaining(1500); // 25 minutes

      expect(useSessionStore.getState().timeRemaining).toBe(1500);
    });

    it("should decrement time", () => {
      const store = useSessionStore.getState();
      store.setTimeRemaining(100);
      store.decrementTime();

      expect(useSessionStore.getState().timeRemaining).toBe(99);
    });

    it("should not decrement below 0", () => {
      const store = useSessionStore.getState();
      store.setTimeRemaining(0);
      store.decrementTime();

      expect(useSessionStore.getState().timeRemaining).toBe(0);
    });
  });

  describe("participant management", () => {
    beforeEach(() => {
      useSessionStore.getState().setSession("session-1", "table-1", [mockParticipant]);
    });

    it("should add participant", () => {
      const store = useSessionStore.getState();
      const newParticipant: Participant = {
        ...mockParticipant,
        id: "user-2",
        username: "newuser",
      };
      store.addParticipant(newParticipant);

      expect(useSessionStore.getState().participants).toHaveLength(2);
    });

    it("should update participant", () => {
      const store = useSessionStore.getState();
      store.updateParticipant("user-1", { isMuted: true });

      const participant = useSessionStore.getState().participants[0];
      expect(participant.isMuted).toBe(true);
    });

    it("should remove participant", () => {
      const store = useSessionStore.getState();
      store.removeParticipant("user-1");

      expect(useSessionStore.getState().participants).toHaveLength(0);
    });
  });

  describe("matching", () => {
    it("should set matching state with timestamp", () => {
      const store = useSessionStore.getState();
      store.setMatching(true);

      const state = useSessionStore.getState();
      expect(state.isMatching).toBe(true);
      expect(state.matchingStartedAt).toBeInstanceOf(Date);
    });

    it("should clear timestamp when matching ends", () => {
      const store = useSessionStore.getState();
      store.setMatching(true);
      store.setMatching(false);

      const state = useSessionStore.getState();
      expect(state.isMatching).toBe(false);
      expect(state.matchingStartedAt).toBeNull();
    });
  });

  describe("audio controls", () => {
    it("should toggle mute state", () => {
      const store = useSessionStore.getState();
      store.setMuted(true);

      expect(useSessionStore.getState().isMuted).toBe(true);

      store.setMuted(false);
      expect(useSessionStore.getState().isMuted).toBe(false);
    });

    it("should toggle quiet mode", () => {
      const store = useSessionStore.getState();
      store.setQuietMode(true);

      expect(useSessionStore.getState().isQuietMode).toBe(true);
    });
  });

  describe("leaveSession", () => {
    it("should reset session state but keep phase as idle", () => {
      const store = useSessionStore.getState();
      store.setSession("session-1", "table-1", [mockParticipant]);
      store.setPhase("work1");
      store.setTimeRemaining(1500);

      store.leaveSession();

      const state = useSessionStore.getState();
      expect(state.sessionId).toBeNull();
      expect(state.tableId).toBeNull();
      expect(state.participants).toHaveLength(0);
      expect(state.currentPhase).toBe("idle");
      expect(state.timeRemaining).toBe(0);
    });
  });

  describe("waiting room", () => {
    it("should set waiting room state", () => {
      const store = useSessionStore.getState();
      const startTime = new Date("2026-02-13T10:00:00Z");
      store.setWaitingRoom(startTime, 5, false);

      const state = useSessionStore.getState();
      expect(state.sessionStartTime).toEqual(startTime);
      expect(state.waitMinutes).toBe(5);
      expect(state.isWaiting).toBe(true);
      expect(state.isImmediate).toBe(false);
    });

    it("should set immediate waiting room", () => {
      const store = useSessionStore.getState();
      const startTime = new Date("2026-02-13T10:00:00Z");
      store.setWaitingRoom(startTime, 0, true);

      const state = useSessionStore.getState();
      expect(state.isImmediate).toBe(true);
      expect(state.waitMinutes).toBe(0);
    });

    it("should clear waiting room but keep sessionStartTime", () => {
      const store = useSessionStore.getState();
      const startTime = new Date("2026-02-13T10:00:00Z");
      store.setWaitingRoom(startTime, 5, false);
      store.clearWaitingRoom();

      const state = useSessionStore.getState();
      // sessionStartTime is preserved (needed for timer calculation)
      expect(state.sessionStartTime).toEqual(startTime);
      // Waiting-specific flags are cleared
      expect(state.waitMinutes).toBeNull();
      expect(state.isWaiting).toBe(false);
      expect(state.isImmediate).toBe(false);
    });
  });

  describe("LiveKit connection", () => {
    it("should set LiveKit connection details", () => {
      const store = useSessionStore.getState();
      store.setLiveKitConnection("token-abc123", "wss://livekit.example.com");

      const state = useSessionStore.getState();
      expect(state.livekitToken).toBe("token-abc123");
      expect(state.livekitServerUrl).toBe("wss://livekit.example.com");
    });

    it("should clear LiveKit connection and reset connected state", () => {
      const store = useSessionStore.getState();
      store.setLiveKitConnection("token-abc123", "wss://livekit.example.com");
      store.setConnected(true);
      store.clearLiveKitConnection();

      const state = useSessionStore.getState();
      expect(state.livekitToken).toBeNull();
      expect(state.livekitServerUrl).toBeNull();
      expect(state.isConnected).toBe(false);
    });
  });

  describe("connection state", () => {
    it("should set connected to true", () => {
      const store = useSessionStore.getState();
      store.setConnected(true);

      expect(useSessionStore.getState().isConnected).toBe(true);
    });

    it("should set connected to false", () => {
      const store = useSessionStore.getState();
      store.setConnected(true);
      store.setConnected(false);

      expect(useSessionStore.getState().isConnected).toBe(false);
    });
  });

  describe("activity tracking", () => {
    it("should enable activity tracking", () => {
      const store = useSessionStore.getState();
      store.setActivityTrackingEnabled(true);

      expect(useSessionStore.getState().activityTrackingEnabled).toBe(true);
    });

    it("should disable activity tracking", () => {
      const store = useSessionStore.getState();
      store.setActivityTrackingEnabled(true);
      store.setActivityTrackingEnabled(false);

      expect(useSessionStore.getState().activityTrackingEnabled).toBe(false);
    });
  });

  describe("end modal", () => {
    it("should show end modal", () => {
      const store = useSessionStore.getState();
      store.setShowEndModal(true);

      expect(useSessionStore.getState().showEndModal).toBe(true);
    });

    it("should hide end modal", () => {
      const store = useSessionStore.getState();
      store.setShowEndModal(true);
      store.setShowEndModal(false);

      expect(useSessionStore.getState().showEndModal).toBe(false);
    });
  });

  describe("reset", () => {
    it("should reset all state to initial values", () => {
      const store = useSessionStore.getState();
      // Set various state
      store.setSession("session-1", "table-1", [mockParticipant]);
      store.setPhase("work1");
      store.setTimeRemaining(1500);
      store.setWaitingRoom(new Date(), 5, false);
      store.setLiveKitConnection("token", "wss://server.com");
      store.setConnected(true);
      store.setShowEndModal(true);

      store.reset();

      const state = useSessionStore.getState();
      expect(state.sessionId).toBeNull();
      expect(state.tableId).toBeNull();
      expect(state.participants).toHaveLength(0);
      expect(state.currentPhase).toBe("idle");
      expect(state.timeRemaining).toBe(0);
      expect(state.isWaiting).toBe(false);
      expect(state.livekitToken).toBeNull();
      expect(state.isConnected).toBe(false);
      expect(state.showEndModal).toBe(false);
    });
  });
});
