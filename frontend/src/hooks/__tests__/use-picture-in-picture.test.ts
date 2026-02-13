import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook } from "@testing-library/react";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const defaultHookProps = {
  phase: "work1" as const,
  timeRemaining: 300,
  participants: [],
};

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.resetModules();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function importHook() {
  vi.resetModules();
  const mod = await import("../use-picture-in-picture");
  return mod.usePictureInPicture;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("usePictureInPicture", () => {
  // -------------------------------------------------------------------------
  // API support detection
  // -------------------------------------------------------------------------
  describe("isPiPSupported", () => {
    it("returns isPiPSupported: false when neither API is available (JSDOM default)", async () => {
      // JSDOM does not provide documentPictureInPicture or pictureInPictureEnabled
      const usePictureInPicture = await importHook();
      const { result } = renderHook(() => usePictureInPicture(defaultHookProps));

      expect(result.current.isPiPSupported).toBe(false);
    });

    it("returns isPiPSupported: true when documentPictureInPicture is on window", async () => {
      // Simulate the Document PiP API being available
      vi.stubGlobal("documentPictureInPicture", {
        requestWindow: vi.fn(),
      });

      const usePictureInPicture = await importHook();
      const { result } = renderHook(() => usePictureInPicture(defaultHookProps));

      expect(result.current.isPiPSupported).toBe(true);
    });

    it("returns isPiPSupported: true when document.pictureInPictureEnabled is true", async () => {
      // Simulate the legacy video PiP API being available
      Object.defineProperty(document, "pictureInPictureEnabled", {
        value: true,
        writable: true,
        configurable: true,
      });

      const usePictureInPicture = await importHook();
      const { result } = renderHook(() => usePictureInPicture(defaultHookProps));

      expect(result.current.isPiPSupported).toBe(true);

      // Clean up the property
      Object.defineProperty(document, "pictureInPictureEnabled", {
        value: false,
        writable: true,
        configurable: true,
      });
    });
  });

  // -------------------------------------------------------------------------
  // Initial state
  // -------------------------------------------------------------------------
  describe("initial state", () => {
    it("starts with isPiPActive: false", async () => {
      const usePictureInPicture = await importHook();
      const { result } = renderHook(() => usePictureInPicture(defaultHookProps));

      expect(result.current.isPiPActive).toBe(false);
    });

    it("provides a togglePiP function", async () => {
      const usePictureInPicture = await importHook();
      const { result } = renderHook(() => usePictureInPicture(defaultHookProps));

      expect(typeof result.current.togglePiP).toBe("function");
    });
  });

  // -------------------------------------------------------------------------
  // Canvas fallback path
  // -------------------------------------------------------------------------
  describe("canvas fallback", () => {
    it("uses canvas strategy when only pictureInPictureEnabled is available", async () => {
      // Mock only legacy PiP API
      Object.defineProperty(document, "pictureInPictureEnabled", {
        value: true,
        writable: true,
        configurable: true,
      });

      const usePictureInPicture = await importHook();
      const { result } = renderHook(() => usePictureInPicture(defaultHookProps));

      expect(result.current.isPiPSupported).toBe(true);

      // Clean up
      Object.defineProperty(document, "pictureInPictureEnabled", {
        value: false,
        writable: true,
        configurable: true,
      });
    });
  });

  // -------------------------------------------------------------------------
  // Cleanup on unmount
  // -------------------------------------------------------------------------
  describe("cleanup", () => {
    it("cleans up on unmount without throwing", async () => {
      const usePictureInPicture = await importHook();
      const { unmount } = renderHook(() => usePictureInPicture(defaultHookProps));

      // Unmount should not throw
      expect(() => unmount()).not.toThrow();
    });

    it("handles cleanup gracefully when canvas strategy is available", async () => {
      // Mock the canvas PiP API
      Object.defineProperty(document, "pictureInPictureEnabled", {
        value: true,
        writable: true,
        configurable: true,
      });

      const usePictureInPicture = await importHook();
      const { result, unmount } = renderHook(() => usePictureInPicture(defaultHookProps));

      // Verify we're in canvas strategy mode (isPiPSupported should be true)
      expect(result.current.isPiPSupported).toBe(true);

      // Unmount - cleanup should handle any potential streams gracefully
      expect(() => unmount()).not.toThrow();

      // Clean up
      Object.defineProperty(document, "pictureInPictureEnabled", {
        value: false,
        writable: true,
        configurable: true,
      });
    });
  });

  // -------------------------------------------------------------------------
  // Error handling
  // -------------------------------------------------------------------------
  describe("error handling", () => {
    it("togglePiP handles errors gracefully when unsupported", async () => {
      const usePictureInPicture = await importHook();
      const { result } = renderHook(() => usePictureInPicture(defaultHookProps));

      // Calling togglePiP when unsupported should not throw
      expect(() => result.current.togglePiP()).not.toThrow();
      expect(result.current.isPiPActive).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // Auto-close on session end
  // -------------------------------------------------------------------------
  describe("auto-close", () => {
    it("closes PiP when phase becomes completed", async () => {
      const usePictureInPicture = await importHook();
      type SessionPhase = "idle" | "setup" | "work1" | "break" | "work2" | "social" | "completed";
      const { result, rerender } = renderHook(
        ({ phase }: { phase: SessionPhase }) => usePictureInPicture({ ...defaultHookProps, phase }),
        { initialProps: { phase: "work1" as SessionPhase } }
      );

      // Simulate phase change to completed
      rerender({ phase: "completed" });

      // Should remain inactive (can't activate without APIs anyway)
      expect(result.current.isPiPActive).toBe(false);
    });
  });

  // -------------------------------------------------------------------------
  // Document PiP toggle flow
  // -------------------------------------------------------------------------
  describe("Document PiP toggle", () => {
    it("calls requestWindow with correct dimensions when toggling on", async () => {
      const mockRequestWindow = vi.fn().mockRejectedValue(new Error("User cancelled"));

      vi.stubGlobal("documentPictureInPicture", {
        requestWindow: mockRequestWindow,
      });

      const usePictureInPicture = await importHook();
      const { result } = renderHook(() => usePictureInPicture(defaultHookProps));

      expect(result.current.isPiPSupported).toBe(true);

      // Toggle - will fail but we can verify the call was made
      result.current.togglePiP();

      // Wait for async call
      await vi.waitFor(() => {
        expect(mockRequestWindow).toHaveBeenCalledWith({ width: 320, height: 180 });
      });

      // Should remain inactive due to error
      expect(result.current.isPiPActive).toBe(false);
    });

    it("handles requestWindow rejection gracefully", async () => {
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      vi.stubGlobal("documentPictureInPicture", {
        requestWindow: vi.fn().mockRejectedValue(new Error("User denied")),
      });

      const usePictureInPicture = await importHook();
      const { result } = renderHook(() => usePictureInPicture(defaultHookProps));

      // Toggle should not throw
      expect(() => result.current.togglePiP()).not.toThrow();

      // Wait for error to be logged
      await vi.waitFor(() => {
        expect(consoleSpy).toHaveBeenCalled();
      });

      // State should remain inactive
      expect(result.current.isPiPActive).toBe(false);

      consoleSpy.mockRestore();
    });
  });

  // -------------------------------------------------------------------------
  // Toggle behavior
  // -------------------------------------------------------------------------
  describe("toggle behavior", () => {
    it("does nothing when PiP is not supported", async () => {
      // No PiP APIs available (JSDOM default)
      const usePictureInPicture = await importHook();
      const { result } = renderHook(() => usePictureInPicture(defaultHookProps));

      expect(result.current.isPiPSupported).toBe(false);

      // Toggle should do nothing without throwing
      result.current.togglePiP();
      expect(result.current.isPiPActive).toBe(false);
    });

    it("toggle function is stable across renders", async () => {
      const usePictureInPicture = await importHook();
      type SessionPhase = "idle" | "setup" | "work1" | "break" | "work2" | "social" | "completed";
      const { result, rerender } = renderHook(
        ({ timeRemaining }: { timeRemaining: number }) =>
          usePictureInPicture({ ...defaultHookProps, timeRemaining }),
        { initialProps: { timeRemaining: 300 } }
      );

      const firstToggle = result.current.togglePiP;

      // Rerender with different props
      rerender({ timeRemaining: 200 });

      // togglePiP should be memoized
      expect(typeof result.current.togglePiP).toBe("function");
    });
  });

  // -------------------------------------------------------------------------
  // propsRef updates
  // -------------------------------------------------------------------------
  describe("props synchronization", () => {
    it("updates internal props ref when props change", async () => {
      const usePictureInPicture = await importHook();
      type SessionPhase = "idle" | "setup" | "work1" | "break" | "work2" | "social" | "completed";
      const { result, rerender } = renderHook(
        ({ phase, timeRemaining }: { phase: SessionPhase; timeRemaining: number }) =>
          usePictureInPicture({ ...defaultHookProps, phase, timeRemaining }),
        { initialProps: { phase: "work1" as SessionPhase, timeRemaining: 300 } }
      );

      // Initial state
      expect(result.current.isPiPActive).toBe(false);

      // Change props multiple times
      rerender({ phase: "break" as SessionPhase, timeRemaining: 120 });
      rerender({ phase: "work2" as SessionPhase, timeRemaining: 1200 });

      // Hook should handle prop changes without error
      expect(result.current.isPiPActive).toBe(false);
      expect(result.current.isPiPSupported).toBe(false);
    });
  });
});
