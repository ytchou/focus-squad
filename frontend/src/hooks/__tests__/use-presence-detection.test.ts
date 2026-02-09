import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { usePresenceDetection } from "../use-presence-detection";

const GRACE_TIMEOUT = 2 * 60 * 1000;
const AWAY_TIMEOUT = 5 * 60 * 1000;
const TICK_INTERVAL = 10 * 1000;
const TYPING_TIMEOUT = 3 * 1000;

function setPageVisibility(state: "visible" | "hidden") {
  Object.defineProperty(document, "visibilityState", {
    value: state,
    configurable: true,
  });
  document.dispatchEvent(new Event("visibilitychange"));
}

describe("usePresenceDetection", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      configurable: true,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // ---------------------------------------------------------------
  // 1. Page visible + recent activity -> "active"
  // ---------------------------------------------------------------
  it('returns "active" when page is visible and activity is recent', () => {
    const { result } = renderHook(() =>
      usePresenceDetection({
        enabled: true,
        inputTrackingConsent: true,
      })
    );

    expect(result.current.presenceState).toBe("active");
    expect(result.current.isPageVisible).toBe(true);

    // After one tick, still active since no time has meaningfully elapsed
    act(() => {
      vi.advanceTimersByTime(TICK_INTERVAL);
    });

    expect(result.current.presenceState).toBe("active");
  });

  // ---------------------------------------------------------------
  // 2. Page hidden within 2 min -> "grace"
  // ---------------------------------------------------------------
  it('transitions to "grace" when page becomes hidden within the grace window', () => {
    const { result } = renderHook(() =>
      usePresenceDetection({
        enabled: true,
        inputTrackingConsent: true,
      })
    );

    act(() => {
      setPageVisibility("hidden");
    });

    // Tick so the interval fires and derives the new state
    act(() => {
      vi.advanceTimersByTime(TICK_INTERVAL);
    });

    expect(result.current.presenceState).toBe("grace");
    expect(result.current.isPageVisible).toBe(false);
  });

  // ---------------------------------------------------------------
  // 3. 2-5 min elapsed -> "away"
  // ---------------------------------------------------------------
  it('transitions to "away" after the grace timeout elapses', () => {
    const { result } = renderHook(() =>
      usePresenceDetection({
        enabled: true,
        inputTrackingConsent: true,
      })
    );

    act(() => {
      setPageVisibility("hidden");
    });

    // Advance past GRACE_TIMEOUT (2 min) but within AWAY_TIMEOUT (5 min)
    act(() => {
      vi.advanceTimersByTime(GRACE_TIMEOUT + TICK_INTERVAL);
    });

    expect(result.current.presenceState).toBe("away");
  });

  // ---------------------------------------------------------------
  // 4. 5 min+ elapsed -> "ghosting"
  // ---------------------------------------------------------------
  it('transitions to "ghosting" after the away timeout elapses', () => {
    const { result } = renderHook(() =>
      usePresenceDetection({
        enabled: true,
        inputTrackingConsent: true,
      })
    );

    act(() => {
      setPageVisibility("hidden");
    });

    // Advance past AWAY_TIMEOUT (5 min)
    act(() => {
      vi.advanceTimersByTime(AWAY_TIMEOUT + TICK_INTERVAL);
    });

    expect(result.current.presenceState).toBe("ghosting");
  });

  // ---------------------------------------------------------------
  // 5. Without consent: only visibility drives state
  // ---------------------------------------------------------------
  describe("without input tracking consent", () => {
    it("does not register input event listeners", () => {
      const addSpy = vi.spyOn(window, "addEventListener");

      renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: false,
        })
      );

      const inputEvents = ["keydown", "mousedown", "mousemove", "touchstart"];
      for (const eventName of inputEvents) {
        const calls = addSpy.mock.calls.filter(([e]) => e === eventName);
        expect(calls).toHaveLength(0);
      }

      addSpy.mockRestore();
    });

    it("still tracks visibility changes for state derivation", () => {
      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: false,
        })
      );

      act(() => {
        setPageVisibility("hidden");
      });

      act(() => {
        vi.advanceTimersByTime(TICK_INTERVAL);
      });

      expect(result.current.presenceState).toBe("grace");

      // Return to visible resets signal, so state goes back to active
      act(() => {
        setPageVisibility("visible");
      });
      act(() => {
        vi.advanceTimersByTime(TICK_INTERVAL);
      });

      expect(result.current.presenceState).toBe("active");
    });

    it("input events do not reset lastSignalAt when consent is false", () => {
      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: false,
        })
      );

      // Advance time so we'd be in "away" if no signal refresh
      act(() => {
        vi.advanceTimersByTime(GRACE_TIMEOUT + TICK_INTERVAL);
      });

      // Dispatch input - should NOT reset the timer without consent
      act(() => {
        window.dispatchEvent(new Event("keydown"));
      });

      act(() => {
        vi.advanceTimersByTime(TICK_INTERVAL);
      });

      // Should still be "away" because keydown was not registered
      expect(result.current.presenceState).toBe("away");
    });
  });

  // ---------------------------------------------------------------
  // 6. State transitions fire onStateChange callback
  // ---------------------------------------------------------------
  describe("onStateChange callback", () => {
    it("fires when state transitions from active to grace", () => {
      const onStateChange = vi.fn();

      renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: true,
          onStateChange,
        })
      );

      act(() => {
        setPageVisibility("hidden");
      });

      act(() => {
        vi.advanceTimersByTime(TICK_INTERVAL);
      });

      expect(onStateChange).toHaveBeenCalledWith("grace", "active");
    });

    it("fires on each distinct state transition", () => {
      const onStateChange = vi.fn();

      renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: true,
          onStateChange,
        })
      );

      // active -> grace
      act(() => {
        setPageVisibility("hidden");
      });
      act(() => {
        vi.advanceTimersByTime(TICK_INTERVAL);
      });
      expect(onStateChange).toHaveBeenCalledWith("grace", "active");

      // grace -> away
      act(() => {
        vi.advanceTimersByTime(GRACE_TIMEOUT);
      });
      expect(onStateChange).toHaveBeenCalledWith("away", "grace");

      // away -> ghosting
      act(() => {
        vi.advanceTimersByTime(AWAY_TIMEOUT - GRACE_TIMEOUT);
      });
      expect(onStateChange).toHaveBeenCalledWith("ghosting", "away");
    });

    it("does not fire when state stays the same", () => {
      const onStateChange = vi.fn();

      renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: true,
          onStateChange,
        })
      );

      // Multiple ticks with page visible and recent activity -> stays "active"
      act(() => {
        vi.advanceTimersByTime(TICK_INTERVAL);
      });
      act(() => {
        vi.advanceTimersByTime(TICK_INTERVAL);
      });

      expect(onStateChange).not.toHaveBeenCalled();
    });
  });

  // ---------------------------------------------------------------
  // 7. Input events update lastSignalAt when consent is granted
  // ---------------------------------------------------------------
  describe("input event signal recording", () => {
    it("keydown resets lastSignalAt and keeps state active", () => {
      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: true,
        })
      );

      // Advance most of the grace timeout
      act(() => {
        vi.advanceTimersByTime(GRACE_TIMEOUT - TICK_INTERVAL);
      });

      // Fire a keydown to reset the signal
      act(() => {
        window.dispatchEvent(new Event("keydown"));
      });

      // Advance another tick - should still be active because signal was refreshed
      act(() => {
        vi.advanceTimersByTime(TICK_INTERVAL);
      });

      expect(result.current.presenceState).toBe("active");
    });

    it("mousedown resets lastSignalAt", () => {
      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: true,
        })
      );

      // Advance close to grace timeout
      act(() => {
        vi.advanceTimersByTime(GRACE_TIMEOUT - TICK_INTERVAL);
      });

      act(() => {
        window.dispatchEvent(new Event("mousedown"));
      });

      act(() => {
        vi.advanceTimersByTime(TICK_INTERVAL);
      });

      expect(result.current.presenceState).toBe("active");
    });

    it("returning to visible resets lastSignalAt", () => {
      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: true,
        })
      );

      // Hide page and advance into away territory
      act(() => {
        setPageVisibility("hidden");
      });
      act(() => {
        vi.advanceTimersByTime(GRACE_TIMEOUT + TICK_INTERVAL);
      });

      expect(result.current.presenceState).toBe("away");

      // Make page visible again - this should call recordSignal()
      act(() => {
        setPageVisibility("visible");
      });
      act(() => {
        vi.advanceTimersByTime(TICK_INTERVAL);
      });

      expect(result.current.presenceState).toBe("active");
    });
  });

  // ---------------------------------------------------------------
  // 8. 10s interval ticks transition correctly (fake timers)
  // ---------------------------------------------------------------
  describe("interval tick behavior", () => {
    it("derives state on each 10s tick", () => {
      const onStateChange = vi.fn();

      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: true,
          onStateChange,
        })
      );

      // Hide the page
      act(() => {
        setPageVisibility("hidden");
      });

      // After 1 tick (10s) - should be grace (hidden, < 2min)
      act(() => {
        vi.advanceTimersByTime(TICK_INTERVAL);
      });
      expect(result.current.presenceState).toBe("grace");

      // Keep ticking through to away boundary (2 min total)
      // We already spent 10s, so advance remaining grace time
      act(() => {
        vi.advanceTimersByTime(GRACE_TIMEOUT - TICK_INTERVAL);
      });
      expect(result.current.presenceState).toBe("away");

      // Keep ticking through to ghosting boundary (5 min total)
      act(() => {
        vi.advanceTimersByTime(AWAY_TIMEOUT - GRACE_TIMEOUT);
      });
      expect(result.current.presenceState).toBe("ghosting");
    });

    it("cleans up interval on unmount", () => {
      const clearIntervalSpy = vi.spyOn(global, "clearInterval");

      const { unmount } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: true,
        })
      );

      unmount();

      expect(clearIntervalSpy).toHaveBeenCalled();
      clearIntervalSpy.mockRestore();
    });
  });

  // ---------------------------------------------------------------
  // 9. When disabled, always returns "active"
  // ---------------------------------------------------------------
  describe("disabled mode", () => {
    it('always returns "active" and isPageVisible=true when disabled', () => {
      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: false,
          inputTrackingConsent: true,
        })
      );

      expect(result.current.presenceState).toBe("active");
      expect(result.current.isPageVisible).toBe(true);
    });

    it("does not transition state when disabled even if page is hidden", () => {
      const onStateChange = vi.fn();

      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: false,
          inputTrackingConsent: true,
          onStateChange,
        })
      );

      act(() => {
        setPageVisibility("hidden");
      });

      act(() => {
        vi.advanceTimersByTime(AWAY_TIMEOUT + TICK_INTERVAL);
      });

      expect(result.current.presenceState).toBe("active");
      expect(onStateChange).not.toHaveBeenCalled();
    });

    it("does not register any event listeners when disabled", () => {
      const docAddSpy = vi.spyOn(document, "addEventListener");
      const winAddSpy = vi.spyOn(window, "addEventListener");

      renderHook(() =>
        usePresenceDetection({
          enabled: false,
          inputTrackingConsent: true,
        })
      );

      const visibilityCalls = docAddSpy.mock.calls.filter(([e]) => e === "visibilitychange");
      expect(visibilityCalls).toHaveLength(0);

      const inputEvents = ["keydown", "mousedown", "mousemove", "touchstart"];
      for (const eventName of inputEvents) {
        const calls = winAddSpy.mock.calls.filter(([e]) => e === eventName);
        expect(calls).toHaveLength(0);
      }

      docAddSpy.mockRestore();
      winAddSpy.mockRestore();
    });
  });

  // ---------------------------------------------------------------
  // Typing detection
  // ---------------------------------------------------------------
  describe("typing detection", () => {
    it("sets isTyping to true on keydown", () => {
      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: true,
        })
      );

      expect(result.current.isTyping).toBe(false);

      act(() => {
        window.dispatchEvent(new Event("keydown"));
      });

      expect(result.current.isTyping).toBe(true);
    });

    it("resets isTyping to false after 3s of no typing", () => {
      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: true,
        })
      );

      act(() => {
        window.dispatchEvent(new Event("keydown"));
      });
      expect(result.current.isTyping).toBe(true);

      act(() => {
        vi.advanceTimersByTime(TYPING_TIMEOUT);
      });

      expect(result.current.isTyping).toBe(false);
    });

    it("resets the 3s timer on subsequent keydowns", () => {
      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: true,
        })
      );

      act(() => {
        window.dispatchEvent(new Event("keydown"));
      });

      // Advance 2s, then type again
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      act(() => {
        window.dispatchEvent(new Event("keydown"));
      });

      // After another 2s (4s total from first keydown), still typing
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      expect(result.current.isTyping).toBe(true);

      // After 3s from the second keydown (5s total), resets
      act(() => {
        vi.advanceTimersByTime(1000);
      });
      expect(result.current.isTyping).toBe(false);
    });

    it("does not set isTyping when consent is false", () => {
      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: false,
        })
      );

      act(() => {
        window.dispatchEvent(new Event("keydown"));
      });

      expect(result.current.isTyping).toBe(false);
    });

    it("returns isTyping false when disabled", () => {
      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: false,
          inputTrackingConsent: true,
        })
      );

      expect(result.current.isTyping).toBe(false);
    });

    it("mousedown does not set isTyping", () => {
      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: true,
        })
      );

      act(() => {
        window.dispatchEvent(new Event("mousedown"));
      });

      expect(result.current.isTyping).toBe(false);
    });
  });

  // ---------------------------------------------------------------
  // Edge cases
  // ---------------------------------------------------------------
  describe("edge cases", () => {
    it("visible page but idle for 2+ min transitions to away (not grace)", () => {
      const { result } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: false,
        })
      );

      // Page stays visible but no input events and no consent
      // Advance past GRACE_TIMEOUT
      act(() => {
        vi.advanceTimersByTime(GRACE_TIMEOUT + TICK_INTERVAL);
      });

      // deriveState: isPageVisible=true, elapsed > GRACE_TIMEOUT, elapsed < AWAY_TIMEOUT -> "away"
      expect(result.current.presenceState).toBe("away");
      expect(result.current.isPageVisible).toBe(true);
    });

    it("cleans up input listeners on unmount", () => {
      const removeSpy = vi.spyOn(window, "removeEventListener");

      const { unmount } = renderHook(() =>
        usePresenceDetection({
          enabled: true,
          inputTrackingConsent: true,
        })
      );

      unmount();

      const inputEvents = ["keydown", "mousedown", "mousemove", "touchstart"];
      for (const eventName of inputEvents) {
        const calls = removeSpy.mock.calls.filter(([e]) => e === eventName);
        expect(calls).toHaveLength(1);
      }

      removeSpy.mockRestore();
    });

    it("re-enables detection when enabled toggles from false to true", () => {
      const { result, rerender } = renderHook(
        ({ enabled }: { enabled: boolean }) =>
          usePresenceDetection({
            enabled,
            inputTrackingConsent: true,
          }),
        { initialProps: { enabled: false } }
      );

      expect(result.current.presenceState).toBe("active");

      // Enable detection
      rerender({ enabled: true });

      // Hide and tick
      act(() => {
        setPageVisibility("hidden");
      });
      act(() => {
        vi.advanceTimersByTime(TICK_INTERVAL);
      });

      expect(result.current.presenceState).toBe("grace");
    });
  });
});
