"use client";

import { Clock } from "lucide-react";
import { useCountdown } from "@/hooks/use-countdown";
import { useCreditsStore } from "@/stores";

interface ZeroCreditCardProps {
  onUpgradeClick: () => void;
}

export function ZeroCreditCard({ onUpgradeClick }: ZeroCreditCardProps) {
  const refreshDate = useCreditsStore((s) => s.refreshDate);
  const { countdown } = useCountdown(refreshDate);

  return (
    <button
      onClick={onUpgradeClick}
      className="w-full rounded-2xl border border-warning/40 bg-warning/5 p-4 text-left transition-colors hover:bg-warning/10"
    >
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-warning/20">
          <Clock className="h-5 w-5 text-warning" />
        </div>
        <div className="flex-1">
          <p className="font-medium text-foreground">You&apos;re out of credits</p>
          <p className="text-sm text-muted-foreground">
            Credits refresh in <span className="font-medium text-foreground">{countdown}</span>
          </p>
          <p className="mt-1 text-xs text-accent underline-offset-2 hover:underline">
            View upgrade options &amp; referral
          </p>
        </div>
      </div>
    </button>
  );
}
