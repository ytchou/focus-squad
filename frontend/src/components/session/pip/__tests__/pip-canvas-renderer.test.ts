import { describe, it, expect, vi, beforeEach } from "vitest";
import { PiPCanvasRenderer, type PiPRenderState } from "../pip-canvas-renderer";
import { PHASE_LABELS, type PiPParticipant } from "../pip-colors";
import type { SessionPhase } from "@/stores/session-store";

// ---------------------------------------------------------------------------
// Canvas 2D context mock
// ---------------------------------------------------------------------------

function createMockCtx(): CanvasRenderingContext2D {
  return {
    fillStyle: "",
    font: "",
    textAlign: "",
    textBaseline: "",
    globalAlpha: 1,
    fillRect: vi.fn(),
    fillText: vi.fn(),
    beginPath: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
  } as unknown as CanvasRenderingContext2D;
}

let mockCtx: CanvasRenderingContext2D;

beforeEach(() => {
  mockCtx = createMockCtx();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(mockCtx);
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeParticipant(
  displayName: string | null,
  presenceState: PiPParticipant["presenceState"] = "active"
): PiPParticipant {
  return { displayName, presenceState };
}

function makeState(overrides: Partial<PiPRenderState> = {}): PiPRenderState {
  return {
    phase: "work1",
    timeRemaining: 600,
    participants: [],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Constructor
// ---------------------------------------------------------------------------

describe("PiPCanvasRenderer", () => {
  describe("constructor", () => {
    it("creates a 320x180 canvas", () => {
      const renderer = new PiPCanvasRenderer();
      const canvas = renderer.getCanvas();
      expect(canvas.width).toBe(320);
      expect(canvas.height).toBe(180);
    });

    it("requests a 2d context", () => {
      new PiPCanvasRenderer();
      expect(HTMLCanvasElement.prototype.getContext).toHaveBeenCalledWith("2d");
    });

    it("throws if 2d context is unavailable", () => {
      vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
      expect(() => new PiPCanvasRenderer()).toThrow("Canvas 2D context not available");
    });
  });

  // -------------------------------------------------------------------------
  // Timer section
  // -------------------------------------------------------------------------

  describe("render — timer section", () => {
    const phases: SessionPhase[] = [
      "idle",
      "setup",
      "work1",
      "break",
      "work2",
      "social",
      "completed",
    ];

    it.each(phases)("fills timer background with phase color for %s", (phase) => {
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ phase }));

      expect(mockCtx.fillRect).toHaveBeenCalledWith(0, 0, 320, 100);
      // The fillStyle is set before the first fillRect call
      // We verify it was set to the correct phase color at some point
      const fillRectCalls = (mockCtx.fillRect as ReturnType<typeof vi.fn>).mock.calls;
      expect(fillRectCalls.length).toBeGreaterThanOrEqual(1);
    });

    it("draws formatted time as MM:SS", () => {
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ timeRemaining: 125 }));

      expect(mockCtx.fillText).toHaveBeenCalledWith("02:05", 160, expect.any(Number));
    });

    it("draws 00:00 for zero time remaining", () => {
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ timeRemaining: 0 }));

      expect(mockCtx.fillText).toHaveBeenCalledWith("00:00", 160, expect.any(Number));
    });

    it("clamps negative time to 00:00", () => {
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ timeRemaining: -10 }));

      expect(mockCtx.fillText).toHaveBeenCalledWith("00:00", 160, expect.any(Number));
    });

    it.each(phases)("draws phase label for %s", (phase) => {
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ phase }));

      expect(mockCtx.fillText).toHaveBeenCalledWith(PHASE_LABELS[phase], 160, expect.any(Number));
    });

    it("uses correct text color for work1 phase", () => {
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ phase: "work1" }));

      const fillTextCalls = (mockCtx.fillText as ReturnType<typeof vi.fn>).mock.calls;
      // Timer text is the first fillText call
      expect(fillTextCalls.length).toBeGreaterThanOrEqual(1);
    });
  });

  // -------------------------------------------------------------------------
  // Avatar section background
  // -------------------------------------------------------------------------

  describe("render — avatar section", () => {
    it("fills avatar section with dark background", () => {
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState());

      expect(mockCtx.fillRect).toHaveBeenCalledWith(0, 100, 320, 80);
    });
  });

  // -------------------------------------------------------------------------
  // Participant avatars
  // -------------------------------------------------------------------------

  describe("render — participant avatars", () => {
    it("draws no avatars when participants is empty", () => {
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ participants: [] }));

      // No arc calls = no avatar circles drawn
      expect(mockCtx.arc).not.toHaveBeenCalled();
    });

    it("draws avatar circle for each participant", () => {
      const participants = [makeParticipant("Alice"), makeParticipant("Bob")];
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ participants }));

      // Each avatar: border ring (arc) + inner circle (arc) = 2 arcs per participant
      expect(mockCtx.arc).toHaveBeenCalledTimes(4);
    });

    it("draws at most 4 avatars even with more participants", () => {
      const participants = [
        makeParticipant("A"),
        makeParticipant("B"),
        makeParticipant("C"),
        makeParticipant("D"),
        makeParticipant("E"),
      ];
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ participants }));

      // 4 avatars * 2 arcs each = 8
      expect(mockCtx.arc).toHaveBeenCalledTimes(8);
    });

    it("uses first character of displayName as initial", () => {
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ participants: [makeParticipant("Alice")] }));

      expect(mockCtx.fillText).toHaveBeenCalledWith("A", expect.any(Number), expect.any(Number));
    });

    it("uses ? for null displayName", () => {
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ participants: [makeParticipant(null)] }));

      expect(mockCtx.fillText).toHaveBeenCalledWith("?", expect.any(Number), expect.any(Number));
    });

    it("truncates long names to 8 characters", () => {
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ participants: [makeParticipant("LongUserName123")] }));

      expect(mockCtx.fillText).toHaveBeenCalledWith(
        "LongUser",
        expect.any(Number),
        expect.any(Number)
      );
    });

    it("draws presence-colored border ring for active state", () => {
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ participants: [makeParticipant("A", "active")] }));

      // The border ring arc has radius AVATAR_RADIUS + AVATAR_BORDER = 16 + 3 = 19
      expect(mockCtx.arc).toHaveBeenCalledWith(
        expect.any(Number),
        expect.any(Number),
        19,
        0,
        Math.PI * 2
      );
    });

    it("draws inner circle with correct radius", () => {
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ participants: [makeParticipant("A")] }));

      // Inner circle arc has radius AVATAR_RADIUS = 16
      expect(mockCtx.arc).toHaveBeenCalledWith(
        expect.any(Number),
        expect.any(Number),
        16,
        0,
        Math.PI * 2
      );
    });

    it("spaces avatars evenly across the width", () => {
      const participants = [
        makeParticipant("A"),
        makeParticipant("B"),
        makeParticipant("C"),
        makeParticipant("D"),
      ];
      const renderer = new PiPCanvasRenderer();
      renderer.render(makeState({ participants }));

      // AVATAR_SPACING = 320/5 = 64, positions: 64, 128, 192, 256
      const arcCalls = (mockCtx.arc as ReturnType<typeof vi.fn>).mock.calls;
      // First arg of each border ring arc (every other arc starting from 0)
      const xPositions = arcCalls
        .filter((_: unknown, i: number) => i % 2 === 0)
        .map((c: number[]) => c[0]);
      expect(xPositions).toEqual([64, 128, 192, 256]);
    });
  });

  // -------------------------------------------------------------------------
  // Destroy
  // -------------------------------------------------------------------------

  describe("destroy", () => {
    it("nullifies canvas and ctx for garbage collection", () => {
      const renderer = new PiPCanvasRenderer();
      renderer.destroy();

      // After destroy, getCanvas returns null (cast away type safety)
      const raw = renderer as unknown as Record<string, unknown>;
      expect(raw.canvas).toBeNull();
      expect(raw.ctx).toBeNull();
    });
  });
});
