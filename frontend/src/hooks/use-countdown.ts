"use client";

import { useState, useEffect } from "react";

interface UseCountdownReturn {
  countdown: string;
  isExpired: boolean;
}

function formatCountdown(diffMs: number): string {
  if (diffMs <= 0) return "Now!";

  const totalMinutes = Math.floor(diffMs / 60_000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;

  if (days > 0) return `${days}d ${remainingHours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

/**
 * Hook that counts down to a target date (e.g., credit refresh).
 * Ticks every 60 seconds since credit refresh is day-level precision.
 *
 * @param targetDate - ISO date string to count down to, or null
 * @returns countdown string and whether the target has passed
 */
export function useCountdown(targetDate: string | null): UseCountdownReturn {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!targetDate) return;

    const interval = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(interval);
  }, [targetDate]);

  if (!targetDate) {
    return { countdown: "--", isExpired: false };
  }

  const targetMs = new Date(targetDate).getTime();
  if (Number.isNaN(targetMs)) {
    return { countdown: "--", isExpired: false };
  }

  const diffMs = targetMs - now;
  return {
    countdown: formatCountdown(diffMs),
    isExpired: diffMs <= 0,
  };
}
