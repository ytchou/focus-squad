"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { Flame, Check } from "lucide-react";

interface StreakProgressBarProps {
  sessionCount: number;
  nextBonusAt: number;
  bonus3Awarded: boolean;
  bonus5Awarded: boolean;
  compact?: boolean;
}

export function StreakProgressBar({
  sessionCount,
  nextBonusAt: _nextBonusAt,
  bonus3Awarded,
  bonus5Awarded,
  compact = false,
}: StreakProgressBarProps) {
  const t = useTranslations("streak");

  const allComplete = bonus3Awarded && bonus5Awarded;
  const target = bonus3Awarded ? 5 : 3;
  const progress = Math.min(sessionCount / target, 1);

  const bonusHint = !bonus3Awarded ? t("bonus3") : !bonus5Awarded ? t("bonus5") : null;

  return (
    <div className={cn("rounded-xl bg-surface p-3", compact ? "p-2" : "p-3")}>
      {/* Header row */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <Flame className={cn("text-accent", compact ? "h-3.5 w-3.5" : "h-4 w-4")} />
          <span className={cn("font-medium text-foreground", compact ? "text-xs" : "text-sm")}>
            {t("title")}
          </span>
        </div>
        <span
          className={cn(
            "font-medium",
            allComplete ? "text-success" : "text-muted-foreground",
            compact ? "text-xs" : "text-sm"
          )}
        >
          {allComplete ? t("complete") : t("progress", { count: sessionCount, target })}
        </span>
      </div>

      {/* Progress bar */}
      <div
        className={cn(
          "relative w-full rounded-xl bg-muted overflow-hidden",
          compact ? "h-2" : "h-3"
        )}
      >
        <div
          className={cn(
            "h-full rounded-xl transition-all duration-500 ease-out",
            allComplete ? "bg-success" : "bg-accent"
          )}
          style={{ width: `${progress * 100}%` }}
        />

        {/* Marker at 3/5 position (60%) — only visible when target is 5 */}
        {bonus3Awarded && !bonus5Awarded && (
          <div className="absolute top-0 h-full w-0.5 bg-foreground/20" style={{ left: "60%" }} />
        )}
      </div>

      {/* Milestone markers */}
      {!compact && (
        <div className="flex items-center justify-between mt-1.5">
          <div className="flex items-center gap-1">
            <div
              className={cn(
                "flex h-4 w-4 items-center justify-center rounded-full",
                bonus3Awarded
                  ? "bg-success text-success-foreground"
                  : "bg-muted text-muted-foreground"
              )}
            >
              {bonus3Awarded ? (
                <Check className="h-3 w-3" />
              ) : (
                <span className="text-[10px]">3</span>
              )}
            </div>
            <span className="text-[10px] text-muted-foreground">+1</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-muted-foreground">+2</span>
            <div
              className={cn(
                "flex h-4 w-4 items-center justify-center rounded-full",
                bonus5Awarded
                  ? "bg-success text-success-foreground"
                  : "bg-muted text-muted-foreground"
              )}
            >
              {bonus5Awarded ? (
                <Check className="h-3 w-3" />
              ) : (
                <span className="text-[10px]">5</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Hint text */}
      {!compact && bonusHint && (
        <p className="mt-1 text-[11px] text-muted-foreground text-center">{bonusHint}</p>
      )}
    </div>
  );
}
