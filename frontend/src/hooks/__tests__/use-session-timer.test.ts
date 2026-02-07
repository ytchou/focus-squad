import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSessionTimer } from "../use-session-timer";

describe("useSessionTimer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns idle state when sessionStartTime is null", () => {
    const { result } = renderHook(() => useSessionTimer({ sessionStartTime: null }));

    expect(result.current.phase).toBe("idle");
    expect(result.current.timeRemaining).toBe(0);
    expect(result.current.totalTimeRemaining).toBe(0);
    expect(result.current.progress).toBe(0);
    expect(result.current.isRunning).toBe(false);
  });

  it("returns correct phase when session is in work1", () => {
    // Session started 10 minutes ago -> should be in work1 (3-28 min)
    const startTime = new Date(Date.now() - 10 * 60 * 1000);

    const { result } = renderHook(() => useSessionTimer({ sessionStartTime: startTime }));

    expect(result.current.phase).toBe("work1");
  });

  it("returns correct timeRemaining", () => {
    // Session started 10 minutes ago -> work1 ends at 28 min -> 18 min remaining
    const startTime = new Date(Date.now() - 10 * 60 * 1000);

    const { result } = renderHook(() => useSessionTimer({ sessionStartTime: startTime }));

    // work1 ends at 28 min, we're at 10 min, so 18 min = 1080s remaining
    expect(result.current.timeRemaining).toBe(1080);
  });

  it("calls onPhaseChange when phase transitions", () => {
    const onPhaseChange = vi.fn();

    // Session started 27 min 59 seconds ago -> work1 (3-28 min)
    // After 2 seconds it should transition to break (28-30 min)
    const startTime = new Date(Date.now() - (27 * 60 + 59) * 1000);

    renderHook(() => useSessionTimer({ sessionStartTime: startTime, onPhaseChange }));

    // Initial render: work1, no phase change yet (same as initial)
    expect(onPhaseChange).not.toHaveBeenCalled();

    // Advance timer by 2 seconds -> crosses from 27:59 to 28:01 -> enters break
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(onPhaseChange).toHaveBeenCalledWith("break", "work1");
  });

  it("updates every second (advance timer by 1000ms)", () => {
    // Session started 10 minutes ago
    const startTime = new Date(Date.now() - 10 * 60 * 1000);

    const { result } = renderHook(() => useSessionTimer({ sessionStartTime: startTime }));

    const initialTimeRemaining = result.current.timeRemaining;

    // Advance by 1 second
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    // timeRemaining should decrease by approximately 1 second
    expect(result.current.timeRemaining).toBe(initialTimeRemaining - 1);
  });

  it("returns isRunning=true during active session", () => {
    const startTime = new Date(Date.now() - 10 * 60 * 1000);

    const { result } = renderHook(() => useSessionTimer({ sessionStartTime: startTime }));

    expect(result.current.isRunning).toBe(true);
  });

  it("returns isRunning=false when completed", () => {
    // Session started 60 minutes ago -> well past 55 min -> completed
    const startTime = new Date(Date.now() - 60 * 60 * 1000);

    const { result } = renderHook(() => useSessionTimer({ sessionStartTime: startTime }));

    expect(result.current.phase).toBe("completed");
    expect(result.current.isRunning).toBe(false);
  });

  it("handles string sessionStartTime", () => {
    // Session started 10 minutes ago as ISO string
    const startTime = new Date(Date.now() - 10 * 60 * 1000).toISOString();

    const { result } = renderHook(() => useSessionTimer({ sessionStartTime: startTime }));

    expect(result.current.phase).toBe("work1");
    expect(result.current.isRunning).toBe(true);
  });
});
