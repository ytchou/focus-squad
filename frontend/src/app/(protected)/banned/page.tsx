"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Clock, CheckCircle, Coffee, Headphones, Heart } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useUserStore, type UserProfile } from "@/stores/user-store";

function parseBannedUntil(user: UserProfile | null, searchParams: URLSearchParams): Date | null {
  const paramValue = searchParams.get("until");
  if (paramValue) {
    const parsed = new Date(paramValue);
    if (!isNaN(parsed.getTime())) return parsed;
  }

  if (user) {
    const bannedUntil = (user as unknown as Record<string, unknown>).banned_until;
    if (typeof bannedUntil === "string") {
      const parsed = new Date(bannedUntil);
      if (!isNaN(parsed.getTime())) return parsed;
    }
  }

  return null;
}

function computeRemaining(bannedUntil: Date | null): { seconds: number; expired: boolean } {
  if (!bannedUntil) return { seconds: 0, expired: true };
  const diff = Math.floor((bannedUntil.getTime() - Date.now()) / 1000);
  if (diff <= 0) return { seconds: 0, expired: true };
  return { seconds: diff, expired: false };
}

function formatCountdown(totalSeconds: number): string {
  if (totalSeconds <= 0) return "0:00:00";
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

export default function BannedPage() {
  const t = useTranslations("rating");
  const router = useRouter();
  const searchParams = useSearchParams();
  const user = useUserStore((s) => s.user);

  const bannedUntil = useMemo(() => parseBannedUntil(user, searchParams), [user, searchParams]);

  const initial = computeRemaining(bannedUntil);
  const [secondsRemaining, setSecondsRemaining] = useState<number>(initial.seconds);
  const [isExpired, setIsExpired] = useState(initial.expired);

  const sessionTips = [
    { icon: Clock, text: t("tipOnTime") },
    { icon: Coffee, text: t("tipFocused") },
    { icon: Headphones, text: t("tipRespectful") },
    { icon: Heart, text: t("tipPresent") },
  ];

  useEffect(() => {
    const tick = () => {
      const result = computeRemaining(bannedUntil);
      setSecondsRemaining(result.seconds);
      setIsExpired(result.expired);
    };
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [bannedUntil]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Header card */}
        <div className="rounded-xl border border-warning/30 bg-warning/5 p-6 text-center space-y-4">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-warning/20">
            {isExpired ? (
              <CheckCircle className="h-8 w-8 text-success" />
            ) : (
              <Clock className="h-8 w-8 text-warning" />
            )}
          </div>

          <div className="space-y-2">
            <h1 className="text-xl font-semibold text-foreground">
              {isExpired ? t("pauseLifted") : t("accountPaused")}
            </h1>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {isExpired ? t("pauseLiftedDesc") : t("accountPausedDesc")}
            </p>
          </div>

          {/* Countdown */}
          {!isExpired && bannedUntil && (
            <div className="pt-2">
              <p className="text-xs text-muted-foreground mb-1">{t("timeRemaining")}</p>
              <p className="text-3xl font-mono font-semibold text-warning tabular-nums tracking-wider">
                {formatCountdown(secondsRemaining)}
              </p>
            </div>
          )}
        </div>

        {/* Tips section */}
        {!isExpired && (
          <div className="rounded-xl border bg-card p-5 space-y-4">
            <h2 className="text-sm font-semibold text-foreground">{t("tipsTitle")}</h2>
            <div className="space-y-3">
              {sessionTips.map((tip) => (
                <div key={tip.text} className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
                    <tip.icon className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed pt-1">{tip.text}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action button */}
        <Button
          variant={isExpired ? "default" : "outline"}
          className={cn("w-full", !isExpired && "opacity-50 cursor-not-allowed")}
          disabled={!isExpired}
          onClick={() => router.push("/dashboard")}
        >
          {t("returnToDashboard")}
        </Button>

        {!isExpired && (
          <p className="text-xs text-muted-foreground text-center">
            {t("buttonAvailableWhenPauseEnds")}
          </p>
        )}
      </div>
    </div>
  );
}
