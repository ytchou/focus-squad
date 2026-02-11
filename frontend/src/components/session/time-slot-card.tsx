"use client";

import { useTranslations } from "next-intl";
import { Loader2, Sprout, Users, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface TimeSlotCardProps {
  startTime: string;
  queueCount: number;
  estimatedCount: number;
  hasUserSession: boolean;
  isJoining: boolean;
  isDisabled: boolean;
  disabledReason?: "no_credits" | "pending_ratings";
  onJoin: () => void;
}

export function TimeSlotCard({
  startTime,
  queueCount,
  estimatedCount,
  hasUserSession,
  isJoining,
  isDisabled,
  disabledReason,
  onJoin,
}: TimeSlotCardProps) {
  const t = useTranslations("findTable");

  const formattedTime = new Date(startTime).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });

  const renderSocialProof = () => {
    if (queueCount > 0) {
      return (
        <div className="flex items-center gap-1.5 text-sm text-success">
          <Users className="h-3.5 w-3.5" />
          <span>{t("studyBuddies", { count: queueCount })}</span>
        </div>
      );
    }
    if (estimatedCount > 0) {
      return (
        <div className="text-sm text-muted-foreground">
          {t("usuallyAtThisTime", { count: estimatedCount })}
        </div>
      );
    }
    return (
      <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <Sprout className="h-3.5 w-3.5" />
        <span>{t("beTheFirst")}</span>
      </div>
    );
  };

  const renderDisabledHint = () => {
    if (!isDisabled || !disabledReason) return null;
    return (
      <p className="text-xs text-warning mt-1">
        {disabledReason === "no_credits" ? t("noCreditsHint") : t("pendingRatingsHint")}
      </p>
    );
  };

  if (hasUserSession) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-xl border border-success/40 bg-success/5 p-4">
        <div className="text-lg font-semibold text-foreground">{formattedTime}</div>
        {renderSocialProof()}
        <div className="flex items-center gap-1.5 rounded-lg bg-success/20 px-3 py-1.5 text-sm font-medium text-success">
          <Check className="h-3.5 w-3.5" />
          {t("joined")}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col items-center gap-2 rounded-xl border border-border bg-card p-4 transition-colors",
        !isDisabled && !isJoining && "hover:border-accent/50 hover:bg-accent/5"
      )}
    >
      <div className="text-lg font-semibold text-foreground">{formattedTime}</div>
      {renderSocialProof()}
      {renderDisabledHint()}
      <button
        onClick={onJoin}
        disabled={isDisabled || isJoining}
        className={cn(
          "rounded-lg px-4 py-1.5 text-sm font-medium transition-colors",
          "bg-accent text-accent-foreground hover:bg-accent/90",
          "disabled:opacity-50 disabled:cursor-not-allowed"
        )}
      >
        {isJoining ? (
          <span className="flex items-center gap-1.5">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            {t("joining")}
          </span>
        ) : (
          t("joinSlot")
        )}
      </button>
    </div>
  );
}
