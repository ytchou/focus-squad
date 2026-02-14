"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api/client";
import { ModeToggle } from "./mode-toggle";
import { TimeSlotCard } from "./time-slot-card";

type TableMode = "forced_audio" | "quiet";

interface SlotInfo {
  start_time: string;
  queue_count: number;
  estimated_count: number;
  has_user_session: boolean;
}

interface UpcomingSlotsResponse {
  slots: SlotInfo[];
}

interface FindTableHeroProps {
  onJoinSlot: (slotTime: string, mode: TableMode, topic?: string) => void;
  isMatching: boolean;
  matchingSlot: string | null;
  credits: number;
  hasPendingRatings: boolean;
  initialSlots?: SlotInfo[];
}

const POLL_INTERVAL_MS = 60_000;

export function FindTableHero({
  onJoinSlot,
  isMatching,
  matchingSlot,
  credits,
  hasPendingRatings,
  initialSlots,
}: FindTableHeroProps) {
  const t = useTranslations("findTable");

  const [mode, setMode] = useState<TableMode>("forced_audio");
  const [topic, setTopic] = useState("");
  const [slots, setSlots] = useState<SlotInfo[]>(initialSlots ?? []);
  const [isLoading, setIsLoading] = useState(!initialSlots);

  const fetchSlots = useCallback(async (tableMode: TableMode) => {
    try {
      const data = await api.get<UpcomingSlotsResponse>(
        `/sessions/upcoming-slots?mode=${tableMode}`
      );
      setSlots(data.slots);
    } catch {
      // Silently fail — slots will be empty, user can still try joining
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch on mount and when mode changes (skip first fetch if initialSlots provided)
  const skipInitialFetch = useRef(!!initialSlots);
  useEffect(() => {
    if (skipInitialFetch.current) {
      skipInitialFetch.current = false;
      return;
    }
    setIsLoading(true);
    fetchSlots(mode);
  }, [mode, fetchSlots]);

  // Poll every 60s
  useEffect(() => {
    const interval = setInterval(() => fetchSlots(mode), POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [mode, fetchSlots]);

  const isDisabled = credits === 0 || hasPendingRatings;
  const disabledReason =
    credits === 0
      ? ("no_credits" as const)
      : hasPendingRatings
        ? ("pending_ratings" as const)
        : undefined;

  return (
    <div id="find-table" className="rounded-2xl bg-card p-6 shadow-sm">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">{t("title")}</h2>
          <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
        </div>
        <ModeToggle mode={mode} onChange={setMode} />
      </div>

      {/* Time slot grid */}
      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {slots.map((slot) => (
            <TimeSlotCard
              key={slot.start_time}
              startTime={slot.start_time}
              queueCount={slot.queue_count}
              estimatedCount={slot.estimated_count}
              hasUserSession={slot.has_user_session}
              isJoining={isMatching && matchingSlot === slot.start_time}
              isDisabled={isDisabled || (isMatching && matchingSlot !== slot.start_time)}
              disabledReason={disabledReason}
              onJoin={() => onJoinSlot(slot.start_time, mode, topic || undefined)}
            />
          ))}
        </div>
      )}

      {/* Topic input */}
      <div className="mt-4">
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder={t("topicPlaceholder")}
          maxLength={100}
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>
    </div>
  );
}
