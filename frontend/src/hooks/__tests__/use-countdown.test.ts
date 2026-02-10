import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useCountdown } from "../use-countdown";

describe("useCountdown", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns fallback when targetDate is null", () => {
    const { result } = renderHook(() => useCountdown(null));

    expect(result.current.countdown).toBe("--");
    expect(result.current.isExpired).toBe(false);
  });

  it("formats days and hours correctly", () => {
    const target = new Date(Date.now() + 2 * 24 * 60 * 60_000 + 14 * 60 * 60_000);

    const { result } = renderHook(() => useCountdown(target.toISOString()));

    expect(result.current.countdown).toBe("2d 14h");
    expect(result.current.isExpired).toBe(false);
  });

  it("formats hours and minutes when less than 1 day", () => {
    const target = new Date(Date.now() + 5 * 60 * 60_000 + 30 * 60_000);

    const { result } = renderHook(() => useCountdown(target.toISOString()));

    expect(result.current.countdown).toBe("5h 30m");
    expect(result.current.isExpired).toBe(false);
  });

  it("formats minutes only when less than 1 hour", () => {
    const target = new Date(Date.now() + 45 * 60_000);

    const { result } = renderHook(() => useCountdown(target.toISOString()));

    expect(result.current.countdown).toBe("45m");
    expect(result.current.isExpired).toBe(false);
  });

  it("shows 'Now!' when target date has passed", () => {
    const target = new Date(Date.now() - 60_000);

    const { result } = renderHook(() => useCountdown(target.toISOString()));

    expect(result.current.countdown).toBe("Now!");
    expect(result.current.isExpired).toBe(true);
  });

  it("updates countdown when time advances", () => {
    const target = new Date(Date.now() + 2 * 60 * 60_000 + 30 * 60_000);

    const { result } = renderHook(() => useCountdown(target.toISOString()));
    expect(result.current.countdown).toBe("2h 30m");

    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    expect(result.current.countdown).toBe("2h 29m");
  });

  it("transitions to expired when time runs out", () => {
    const target = new Date(Date.now() + 60_000);

    const { result } = renderHook(() => useCountdown(target.toISOString()));
    expect(result.current.countdown).toBe("1m");
    expect(result.current.isExpired).toBe(false);

    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    expect(result.current.countdown).toBe("Now!");
    expect(result.current.isExpired).toBe(true);
  });

  it("returns fallback for invalid date strings", () => {
    const { result } = renderHook(() => useCountdown("not-a-date"));

    expect(result.current.countdown).toBe("--");
    expect(result.current.isExpired).toBe(false);
  });

  it("shows 0m boundary correctly", () => {
    const target = new Date(Date.now() + 30_000);

    const { result } = renderHook(() => useCountdown(target.toISOString()));

    expect(result.current.countdown).toBe("0m");
    expect(result.current.isExpired).toBe(false);
  });
});
