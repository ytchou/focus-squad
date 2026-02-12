"use client";

import { useTranslations } from "next-intl";
import { UserPlus, Clock, UserCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface AddPartnerButtonProps {
  userId: string;
  partnershipStatus: string | null;
  onSendRequest: (userId: string) => void;
  compact?: boolean;
}

export function AddPartnerButton({
  userId,
  partnershipStatus,
  onSendRequest,
  compact = false,
}: AddPartnerButtonProps) {
  const t = useTranslations("partners");

  if (partnershipStatus === "accepted") {
    return (
      <Button variant="ghost" size={compact ? "xs" : "sm"} disabled className={cn("text-success")}>
        <UserCheck className={compact ? "h-3 w-3" : "h-3.5 w-3.5"} />
        {!compact && t("partnered")}
      </Button>
    );
  }

  if (partnershipStatus === "pending") {
    return (
      <Button
        variant="outline"
        size={compact ? "xs" : "sm"}
        disabled
        className="text-muted-foreground"
      >
        <Clock className={compact ? "h-3 w-3" : "h-3.5 w-3.5"} />
        {!compact && t("pending")}
      </Button>
    );
  }

  return (
    <Button variant="accent" size={compact ? "xs" : "sm"} onClick={() => onSendRequest(userId)}>
      <UserPlus className={compact ? "h-3 w-3" : "h-3.5 w-3.5"} />
      {!compact && t("addPartner")}
    </Button>
  );
}
