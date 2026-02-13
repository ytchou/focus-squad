"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { UserMinus, Clock, MessageCircle, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ReliabilityBadge } from "@/components/ui/reliability-badge";
import { InterestTagBadge } from "./interest-tag-badge";
import type { PartnerInfo } from "@/stores";

interface PartnerCardProps {
  partner: PartnerInfo;
  onRemove: (id: string) => void;
  onMessage?: (userId: string) => void;
  onVisitRoom?: (userId: string) => void;
}

function getRelativeDays(isoDate: string, now: number): number {
  const diff = now - new Date(isoDate).getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24));
}

export function PartnerCard({ partner, onRemove, onMessage, onVisitRoom }: PartnerCardProps) {
  const t = useTranslations("partners");
  const tCommon = useTranslations("common");
  const [confirmRemove, setConfirmRemove] = useState(false);

  const [now] = useState(() => Date.now());

  const relativeTimeLabel = (() => {
    if (!partner.last_session_together) return t("neverStudied");
    const days = getRelativeDays(partner.last_session_together, now);
    if (days === 0) return t("today");
    if (days === 1) return t("yesterday");
    return t("daysAgo", { count: days });
  })();

  const displayName = partner.display_name || partner.username;
  const initial = displayName.charAt(0).toUpperCase();
  const reliabilityScore = partner.reliability_score ? parseFloat(partner.reliability_score) : null;

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent/20 text-accent font-semibold text-sm">
          {initial}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium text-foreground">{displayName}</p>
          <p className="truncate text-sm text-muted-foreground">@{partner.username}</p>
        </div>
      </div>

      {partner.study_interests.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {partner.study_interests.slice(0, 3).map((tag) => (
            <InterestTagBadge key={tag} tag={tag} />
          ))}
          {partner.study_interests.length > 3 && (
            <span className="text-xs text-muted-foreground">
              +{partner.study_interests.length - 3}
            </span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between gap-2">
        {reliabilityScore !== null && <ReliabilityBadge score={reliabilityScore} size="sm" />}
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>{relativeTimeLabel}</span>
        </div>
      </div>

      {confirmRemove ? (
        <div className="flex items-center gap-2">
          <Button
            variant="destructive"
            size="sm"
            className="flex-1"
            onClick={() => onRemove(partner.partnership_id)}
          >
            {t("confirmRemove")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => setConfirmRemove(false)}
          >
            {tCommon("cancel")}
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          {onVisitRoom && (
            <Button variant="outline" size="sm" onClick={() => onVisitRoom(partner.user_id)}>
              <Eye className="h-3.5 w-3.5" />
              {t("visitRoom")}
            </Button>
          )}
          {onMessage && (
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => onMessage(partner.user_id)}
            >
              <MessageCircle className="h-3.5 w-3.5" />
              {t("tabs.messages")}
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground"
            onClick={() => setConfirmRemove(true)}
          >
            <UserMinus className="h-3.5 w-3.5" />
            {t("remove")}
          </Button>
        </div>
      )}
    </div>
  );
}
