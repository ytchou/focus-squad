"use client";

import { useTranslations } from "next-intl";
import type { SessionPhase } from "@/stores/session-store";
import { formatTime, PHASE_LABELS, isWorkPhase } from "@/lib/session/phase-utils";
import { cn } from "@/lib/utils";

interface TimerDisplayProps {
  phase: SessionPhase;
  timeRemaining: number; // seconds
  totalTimeRemaining: number; // seconds
  progress: number; // 0-1 progress through current phase
  compact?: boolean; // Inline badge version for board layout
}

export function TimerDisplay({
  phase,
  timeRemaining,
  totalTimeRemaining,
  progress,
  compact = false,
}: TimerDisplayProps) {
  const t = useTranslations("session");

  if (compact) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1 bg-muted rounded-full">
        <span className="text-sm font-medium text-foreground">{formatTime(timeRemaining)}</span>
        <span className="text-xs text-muted-foreground">{PHASE_LABELS[phase]}</span>
      </div>
    );
  }
  const isWork = isWorkPhase(phase);
  const isBreak = phase === "break";
  const isSocial = phase === "social";

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Circular Progress Ring */}
      <div className="relative">
        <svg className="w-48 h-48 -rotate-90" viewBox="0 0 100 100">
          {/* Background ring */}
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="4"
            className="text-muted"
          />
          {/* Progress ring */}
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="currentColor"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={`${progress * 283} 283`}
            className={cn(
              "transition-all duration-1000",
              isWork && "text-primary",
              isBreak && "text-success",
              isSocial && "text-accent",
              !isWork && !isBreak && !isSocial && "text-muted-foreground"
            )}
          />
        </svg>

        {/* Timer text inside ring */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className={cn(
              "text-4xl font-bold tracking-tight",
              isWork && "text-primary",
              isBreak && "text-success",
              isSocial && "text-accent"
            )}
          >
            {formatTime(timeRemaining)}
          </span>
          <span className="text-sm text-muted-foreground mt-1">{PHASE_LABELS[phase]}</span>
        </div>
      </div>

      {/* Phase guidance text */}
      <PhaseGuidance phase={phase} />

      {/* Total session time remaining (smaller, secondary) */}
      {phase !== "completed" && phase !== "idle" && (
        <p className="text-xs text-muted-foreground">
          {t("totalRemaining", { time: formatTime(totalTimeRemaining) })}
        </p>
      )}
    </div>
  );
}

function PhaseGuidance({ phase }: { phase: SessionPhase }) {
  const t = useTranslations("session");

  const messageKeys: Record<SessionPhase, string> = {
    idle: "guidanceIdle",
    setup: "guidanceSetup",
    work1: "guidanceWork1",
    break: "guidanceBreak",
    work2: "guidanceWork2",
    social: "guidanceSocial",
    completed: "guidanceCompleted",
  };

  const key = messageKeys[phase];
  if (!key) return null;

  return <p className="text-sm text-muted-foreground text-center">{t(key)}</p>;
}
