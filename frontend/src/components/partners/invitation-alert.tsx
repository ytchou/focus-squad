"use client";

import { useTranslations } from "next-intl";
import { Calendar, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { InvitationInfo } from "@/stores";

interface InvitationAlertProps {
  invitation: InvitationInfo;
  onRespond: (sessionId: string, invitationId: string, accept: boolean) => void;
}

export function InvitationAlert({ invitation, onRespond }: InvitationAlertProps) {
  const t = useTranslations("partners");

  const formattedTime = new Date(invitation.session_start_time).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });

  return (
    <div className="flex items-center gap-3 rounded-xl border border-accent/30 bg-accent/5 p-3">
      <Calendar className="h-5 w-5 shrink-0 text-accent" />

      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-foreground">
          {t("invitedBy", { name: invitation.inviter_name })}
        </p>
        <p className="text-xs text-muted-foreground">{t("sessionAt", { time: formattedTime })}</p>
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        <Button
          variant="accent"
          size="xs"
          onClick={() => onRespond(invitation.session_id, invitation.invitation_id, true)}
        >
          <Check className="h-3 w-3" />
          {t("join")}
        </Button>
        <Button
          variant="ghost"
          size="xs"
          className="text-muted-foreground"
          onClick={() => onRespond(invitation.session_id, invitation.invitation_id, false)}
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
    </div>
  );
}
