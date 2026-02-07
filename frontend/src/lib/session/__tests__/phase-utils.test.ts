import { describe, it, expect } from "vitest";
import {
  calculatePhaseInfo,
  formatTime,
  getNextPhase,
  isWorkPhase,
  getPhaseDuration,
  SESSION_DURATION_SECONDS,
} from "../phase-utils";

// Helper: create a start time that is `minutesAgo` minutes before `now`
function startTimeMinutesAgo(minutesAgo: number, now: Date = new Date()): Date {
  return new Date(now.getTime() - minutesAgo * 60 * 1000);
}

describe("calculatePhaseInfo", () => {
  const now = new Date("2025-01-15T12:00:00Z");

  describe("phase boundaries", () => {
    it("returns 'setup' at exactly 0 minutes elapsed", () => {
      const start = startTimeMinutesAgo(0, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("setup");
    });

    it("returns 'setup' at 1.5 minutes elapsed", () => {
      const start = startTimeMinutesAgo(1.5, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("setup");
    });

    it("returns 'setup' at 2.99 minutes elapsed (just before boundary)", () => {
      const start = startTimeMinutesAgo(2.99, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("setup");
    });

    it("returns 'work1' at exactly 3 minutes elapsed", () => {
      const start = startTimeMinutesAgo(3, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("work1");
    });

    it("returns 'work1' at 15 minutes elapsed", () => {
      const start = startTimeMinutesAgo(15, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("work1");
    });

    it("returns 'work1' at 27.99 minutes elapsed (just before break)", () => {
      const start = startTimeMinutesAgo(27.99, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("work1");
    });

    it("returns 'break' at exactly 28 minutes elapsed", () => {
      const start = startTimeMinutesAgo(28, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("break");
    });

    it("returns 'break' at 29 minutes elapsed", () => {
      const start = startTimeMinutesAgo(29, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("break");
    });

    it("returns 'work2' at exactly 30 minutes elapsed", () => {
      const start = startTimeMinutesAgo(30, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("work2");
    });

    it("returns 'work2' at 40 minutes elapsed", () => {
      const start = startTimeMinutesAgo(40, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("work2");
    });

    it("returns 'work2' at 49.99 minutes elapsed (just before social)", () => {
      const start = startTimeMinutesAgo(49.99, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("work2");
    });

    it("returns 'social' at exactly 50 minutes elapsed", () => {
      const start = startTimeMinutesAgo(50, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("social");
    });

    it("returns 'social' at 52 minutes elapsed", () => {
      const start = startTimeMinutesAgo(52, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("social");
    });

    it("returns 'completed' at exactly 55 minutes elapsed", () => {
      const start = startTimeMinutesAgo(55, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("completed");
    });

    it("returns 'completed' at 60 minutes elapsed (well past end)", () => {
      const start = startTimeMinutesAgo(60, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("completed");
    });
  });

  describe("negative elapsed time (before session start)", () => {
    it("returns 'idle' when session hasn't started yet", () => {
      // Start time is 5 minutes in the future
      const start = new Date(now.getTime() + 5 * 60 * 1000);
      const result = calculatePhaseInfo(start, now);
      expect(result.phase).toBe("idle");
    });

    it("returns positive timeRemaining for idle phase", () => {
      const start = new Date(now.getTime() + 5 * 60 * 1000);
      const result = calculatePhaseInfo(start, now);
      expect(result.timeRemaining).toBeCloseTo(300, 0); // 5 min = 300s
    });

    it("returns totalTimeRemaining that includes time until start plus session duration", () => {
      const start = new Date(now.getTime() + 5 * 60 * 1000);
      const result = calculatePhaseInfo(start, now);
      // 5 minutes to start + 55 minutes of session
      expect(result.totalTimeRemaining).toBeCloseTo(SESSION_DURATION_SECONDS + 300, 0);
    });

    it("returns progress=0 for idle phase", () => {
      const start = new Date(now.getTime() + 5 * 60 * 1000);
      const result = calculatePhaseInfo(start, now);
      expect(result.progress).toBe(0);
    });

    it("returns elapsedMinutes=0 for idle phase", () => {
      const start = new Date(now.getTime() + 5 * 60 * 1000);
      const result = calculatePhaseInfo(start, now);
      expect(result.elapsedMinutes).toBe(0);
    });
  });

  describe("timeRemaining calculation", () => {
    it("returns correct timeRemaining at start of setup (3 minutes remaining)", () => {
      const start = startTimeMinutesAgo(0, now);
      const result = calculatePhaseInfo(start, now);
      // Setup is 0-3 min, at 0 min elapsed there are 3 min (180s) left
      expect(result.timeRemaining).toBe(180);
    });

    it("returns correct timeRemaining at start of work1 (25 minutes remaining)", () => {
      const start = startTimeMinutesAgo(3, now);
      const result = calculatePhaseInfo(start, now);
      // Work1 is 3-28 min, at 3 min elapsed there are 25 min (1500s) left
      expect(result.timeRemaining).toBe(1500);
    });

    it("returns correct timeRemaining midway through work1", () => {
      const start = startTimeMinutesAgo(15, now);
      const result = calculatePhaseInfo(start, now);
      // Work1 ends at 28 min, we're at 15 min, so 13 min (780s) left
      expect(result.timeRemaining).toBe(780);
    });

    it("returns correct timeRemaining at start of break (2 minutes remaining)", () => {
      const start = startTimeMinutesAgo(28, now);
      const result = calculatePhaseInfo(start, now);
      // Break is 28-30 min, at 28 min elapsed there are 2 min (120s) left
      expect(result.timeRemaining).toBe(120);
    });

    it("returns 0 timeRemaining for completed phase", () => {
      const start = startTimeMinutesAgo(55, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.timeRemaining).toBe(0);
    });
  });

  describe("totalTimeRemaining calculation", () => {
    it("returns full session duration at start (55 * 60 = 3300s)", () => {
      const start = startTimeMinutesAgo(0, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.totalTimeRemaining).toBe(SESSION_DURATION_SECONDS);
    });

    it("returns correct totalTimeRemaining midway through session", () => {
      const start = startTimeMinutesAgo(25, now);
      const result = calculatePhaseInfo(start, now);
      // 55 - 25 = 30 minutes = 1800 seconds remaining
      expect(result.totalTimeRemaining).toBe(1800);
    });

    it("returns 0 totalTimeRemaining for completed phase", () => {
      const start = startTimeMinutesAgo(55, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.totalTimeRemaining).toBe(0);
    });
  });

  describe("progress calculation", () => {
    it("returns progress=0 at start of setup", () => {
      const start = startTimeMinutesAgo(0, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.progress).toBe(0);
    });

    it("returns progress=0.5 midway through setup (1.5 min of 3 min)", () => {
      const start = startTimeMinutesAgo(1.5, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.progress).toBeCloseTo(0.5, 5);
    });

    it("returns progress=0 at start of work1 (exactly 3 min elapsed)", () => {
      const start = startTimeMinutesAgo(3, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.progress).toBeCloseTo(0, 5);
    });

    it("returns progress near 0.5 midway through work1 (15.5 min elapsed)", () => {
      const start = startTimeMinutesAgo(15.5, now);
      const result = calculatePhaseInfo(start, now);
      // work1 spans 3-28 (25 min); 15.5 - 3 = 12.5 min in; progress = 12.5/25 = 0.5
      expect(result.progress).toBeCloseTo(0.5, 5);
    });

    it("returns progress=1 for completed phase", () => {
      const start = startTimeMinutesAgo(55, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.progress).toBe(1);
    });

    it("progress is always between 0 and 1", () => {
      // Test a range of elapsed values
      const testPoints = [0, 1, 3, 10, 20, 28, 29, 30, 40, 50, 53];
      for (const minutes of testPoints) {
        const start = startTimeMinutesAgo(minutes, now);
        const result = calculatePhaseInfo(start, now);
        expect(result.progress).toBeGreaterThanOrEqual(0);
        expect(result.progress).toBeLessThanOrEqual(1);
      }
    });
  });

  describe("string vs Date input for sessionStartTime", () => {
    it("accepts a string ISO date and returns correct phase", () => {
      // 10 min ago as ISO string
      const startStr = new Date(now.getTime() - 10 * 60 * 1000).toISOString();
      const result = calculatePhaseInfo(startStr, now);
      expect(result.phase).toBe("work1");
    });

    it("string input matches Date input for same time", () => {
      const startDate = startTimeMinutesAgo(15, now);
      const startStr = startDate.toISOString();

      const resultFromDate = calculatePhaseInfo(startDate, now);
      const resultFromString = calculatePhaseInfo(startStr, now);

      expect(resultFromDate.phase).toBe(resultFromString.phase);
      expect(resultFromDate.timeRemaining).toBe(resultFromString.timeRemaining);
      expect(resultFromDate.totalTimeRemaining).toBe(resultFromString.totalTimeRemaining);
      expect(resultFromDate.progress).toBeCloseTo(resultFromString.progress, 10);
    });
  });

  describe("elapsedMinutes", () => {
    it("returns correct elapsedMinutes during work1", () => {
      const start = startTimeMinutesAgo(15, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.elapsedMinutes).toBeCloseTo(15, 5);
    });

    it("returns SESSION_DURATION_MINUTES for completed phase", () => {
      const start = startTimeMinutesAgo(60, now);
      const result = calculatePhaseInfo(start, now);
      expect(result.elapsedMinutes).toBe(55);
    });
  });
});

describe("formatTime", () => {
  it("formats 0 seconds as '00:00'", () => {
    expect(formatTime(0)).toBe("00:00");
  });

  it("formats 61 seconds as '01:01'", () => {
    expect(formatTime(61)).toBe("01:01");
  });

  it("formats 3600 seconds as '60:00'", () => {
    expect(formatTime(3600)).toBe("60:00");
  });

  it("formats negative values as '00:00'", () => {
    expect(formatTime(-10)).toBe("00:00");
    expect(formatTime(-1)).toBe("00:00");
  });

  it("formats 59 seconds as '00:59'", () => {
    expect(formatTime(59)).toBe("00:59");
  });

  it("formats 120 seconds as '02:00'", () => {
    expect(formatTime(120)).toBe("02:00");
  });

  it("handles fractional seconds by flooring", () => {
    expect(formatTime(61.9)).toBe("01:01");
  });
});

describe("getNextPhase", () => {
  it("returns 'setup' as next phase after 'idle'", () => {
    expect(getNextPhase("idle")).toBe("setup");
  });

  it("returns 'work1' as next phase after 'setup'", () => {
    expect(getNextPhase("setup")).toBe("work1");
  });

  it("returns 'break' as next phase after 'work1'", () => {
    expect(getNextPhase("work1")).toBe("break");
  });

  it("returns 'work2' as next phase after 'break'", () => {
    expect(getNextPhase("break")).toBe("work2");
  });

  it("returns 'social' as next phase after 'work2'", () => {
    expect(getNextPhase("work2")).toBe("social");
  });

  it("returns 'completed' as next phase after 'social'", () => {
    expect(getNextPhase("social")).toBe("completed");
  });

  it("returns null after 'completed'", () => {
    expect(getNextPhase("completed")).toBeNull();
  });
});

describe("isWorkPhase", () => {
  it("returns true for 'work1'", () => {
    expect(isWorkPhase("work1")).toBe(true);
  });

  it("returns true for 'work2'", () => {
    expect(isWorkPhase("work2")).toBe(true);
  });

  it("returns false for 'setup'", () => {
    expect(isWorkPhase("setup")).toBe(false);
  });

  it("returns false for 'break'", () => {
    expect(isWorkPhase("break")).toBe(false);
  });

  it("returns false for 'social'", () => {
    expect(isWorkPhase("social")).toBe(false);
  });

  it("returns false for 'idle'", () => {
    expect(isWorkPhase("idle")).toBe(false);
  });

  it("returns false for 'completed'", () => {
    expect(isWorkPhase("completed")).toBe(false);
  });
});

describe("getPhaseDuration", () => {
  it("returns 180 seconds (3 min) for 'setup'", () => {
    expect(getPhaseDuration("setup")).toBe(180);
  });

  it("returns 1500 seconds (25 min) for 'work1'", () => {
    expect(getPhaseDuration("work1")).toBe(1500);
  });

  it("returns 120 seconds (2 min) for 'break'", () => {
    expect(getPhaseDuration("break")).toBe(120);
  });

  it("returns 1200 seconds (20 min) for 'work2'", () => {
    expect(getPhaseDuration("work2")).toBe(1200);
  });

  it("returns 300 seconds (5 min) for 'social'", () => {
    expect(getPhaseDuration("social")).toBe(300);
  });

  it("returns 0 for 'idle'", () => {
    expect(getPhaseDuration("idle")).toBe(0);
  });

  it("returns 0 for 'completed'", () => {
    expect(getPhaseDuration("completed")).toBe(0);
  });
});
