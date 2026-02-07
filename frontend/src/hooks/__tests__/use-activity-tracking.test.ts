import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useActivityTracking } from "../use-activity-tracking";

describe("useActivityTracking", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns isActive=false when disabled", () => {
    const { result } = renderHook(() => useActivityTracking({ enabled: false }));

    expect(result.current.isActive).toBe(false);
    expect(result.current.lastActivityAt).toBeNull();
  });

  it("returns isActive=false initially when enabled", () => {
    const { result } = renderHook(() => useActivityTracking({ enabled: true }));

    expect(result.current.isActive).toBe(false);
  });

  it("sets isActive=true after keydown event", () => {
    const { result } = renderHook(() => useActivityTracking({ enabled: true }));

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }));
    });

    expect(result.current.isActive).toBe(true);
  });

  it("sets isActive=false after 30s timeout", () => {
    const { result } = renderHook(() => useActivityTracking({ enabled: true }));

    // Trigger activity
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }));
    });

    expect(result.current.isActive).toBe(true);

    // Advance past the 30s timeout
    act(() => {
      vi.advanceTimersByTime(30 * 1000);
    });

    expect(result.current.isActive).toBe(false);
  });

  it("calls onActivityChange callback on state change", () => {
    const onActivityChange = vi.fn();

    renderHook(() => useActivityTracking({ enabled: true, onActivityChange }));

    // Trigger activity -> isActive becomes true
    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }));
    });

    expect(onActivityChange).toHaveBeenCalledWith(true);

    // Wait for timeout -> isActive becomes false
    act(() => {
      vi.advanceTimersByTime(30 * 1000);
    });

    expect(onActivityChange).toHaveBeenCalledWith(false);
    expect(onActivityChange).toHaveBeenCalledTimes(2);
  });

  it("returns lastActivityAt timestamp after activity", () => {
    const now = new Date("2025-01-15T12:00:00Z");
    vi.setSystemTime(now);

    const { result } = renderHook(() => useActivityTracking({ enabled: true }));

    expect(result.current.lastActivityAt).toBeNull();

    act(() => {
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "a" }));
    });

    expect(result.current.lastActivityAt).toEqual(now);
  });
});
