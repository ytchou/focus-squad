"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { UserPlus, Clock, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { PartnerRequestInfo } from "@/stores";

interface PartnerRequestCardProps {
  request: PartnerRequestInfo;
  onRespond: (id: string, accept: boolean) => void;
}

function getRelativeHours(isoDate: string, now: number): number {
  const diff = now - new Date(isoDate).getTime();
  return Math.floor(diff / (1000 * 60 * 60));
}

export function PartnerRequestCard({ request, onRespond }: PartnerRequestCardProps) {
  const t = useTranslations("partners");

  const [now] = useState(() => Date.now());

  const timestampLabel = (() => {
    const hours = getRelativeHours(request.created_at, now);
    if (hours < 1) return t("justNow");
    if (hours < 24) return t("hoursAgo", { count: hours });
    const days = Math.floor(hours / 24);
    return t("daysAgo", { count: days });
  })();

  const displayName = request.display_name || request.username;
  const initial = displayName.charAt(0).toUpperCase();
  const isIncoming = request.direction === "incoming";

  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent/20 text-accent font-semibold text-sm">
        {initial}
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-foreground">{displayName}</p>
        <p className="text-sm text-muted-foreground">
          {isIncoming ? t("wantsToBePartner") : t("pendingRequest")}
        </p>
        <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>{timestampLabel}</span>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {isIncoming ? (
          <>
            <Button
              variant="accent"
              size="sm"
              onClick={() => onRespond(request.partnership_id, true)}
            >
              <UserPlus className="h-3.5 w-3.5" />
              {t("accept")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onRespond(request.partnership_id, false)}
            >
              {t("decline")}
            </Button>
          </>
        ) : (
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground"
            onClick={() => onRespond(request.partnership_id, false)}
          >
            <X className="h-3.5 w-3.5" />
            {t("cancel")}
          </Button>
        )}
      </div>
    </div>
  );
}
