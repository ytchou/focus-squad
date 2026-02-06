"use client";

import type { SessionPhase } from "@/stores/session-store";
import { formatTime, PHASE_LABELS, isWorkPhase } from "@/lib/session/phase-utils";
import { cn } from "@/lib/utils";

interface TimerDisplayProps {
  phase: SessionPhase;
  timeRemaining: number; // seconds
  totalTimeRemaining: number; // seconds
  progress: number; // 0-1 progress through current phase
}

export function TimerDisplay({
  phase,
  timeRemaining,
  totalTimeRemaining,
  progress,
}: TimerDisplayProps) {
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
          {formatTime(totalTimeRemaining)} total remaining
        </p>
      )}
    </div>
  );
}

function PhaseGuidance({ phase }: { phase: SessionPhase }) {
  const messages: Record<SessionPhase, string | null> = {
    idle: "Waiting to start...",
    setup: "Get settled and prepare to focus",
    work1: "Deep work time - stay focused!",
    break: "Take a short break",
    work2: "Final work block - finish strong!",
    social: "Chat with your tablemates",
    completed: "Great session!",
  };

  const message = messages[phase];
  if (!message) return null;

  return <p className="text-sm text-muted-foreground text-center">{message}</p>;
}
