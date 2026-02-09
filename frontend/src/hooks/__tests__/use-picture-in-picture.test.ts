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
});
