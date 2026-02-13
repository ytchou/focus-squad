"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { usePartnerStore } from "@/stores/partner-store";
import { useShopStore } from "@/stores/shop-store";
import { Users, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function PartnerGiftSelector() {
  const t = useTranslations("shop");
  const partners = usePartnerStore((s) => s.partners);
  const fetchPartners = usePartnerStore((s) => s.fetchPartners);
  const selectedRecipientId = useShopStore((s) => s.selectedRecipientId);
  const setGiftingMode = useShopStore((s) => s.setGiftingMode);

  useEffect(() => {
    if (partners.length === 0) {
      fetchPartners();
    }
  }, [partners.length, fetchPartners]);

  if (partners.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-2 text-sm text-muted-foreground">
        <Users className="h-4 w-4" />
        {t("noPartners")}
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-medium text-muted-foreground">{t("selectPartner")}</p>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {partners.map((partner) => {
          const isSelected = selectedRecipientId === partner.user_id;
          return (
            <button
              key={partner.user_id}
              className={cn(
                "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm whitespace-nowrap transition-colors border",
                isSelected
                  ? "bg-accent/20 border-accent text-accent"
                  : "bg-card border-border text-foreground hover:bg-muted/50"
              )}
              onClick={() => setGiftingMode(isSelected ? null : partner.user_id)}
            >
              <div className="h-5 w-5 rounded-full bg-muted flex items-center justify-center text-[10px]">
                {(partner.display_name || partner.username).charAt(0).toUpperCase()}
              </div>
              <span>{partner.display_name || partner.username}</span>
              {isSelected && <X className="h-3 w-3" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
