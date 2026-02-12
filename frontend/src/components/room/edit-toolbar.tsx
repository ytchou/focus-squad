"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Save, X, ShoppingBag } from "lucide-react";
import { useRoomStore } from "@/stores/room-store";
import { useUIStore } from "@/stores";

export function EditToolbar() {
  const t = useTranslations("room");
  const saveLayout = useRoomStore((s) => s.saveLayout);
  const exitEditMode = useRoomStore((s) => s.exitEditMode);
  const openModal = useUIStore((s) => s.openModal);

  return (
    <div className="flex items-center gap-2 rounded-xl border border-border bg-card p-2 shadow-sm">
      <Button variant="accent" size="sm" onClick={saveLayout}>
        <Save className="h-4 w-4" />
        {t("save")}
      </Button>
      <Button variant="outline" size="sm" onClick={exitEditMode}>
        <X className="h-4 w-4" />
        {t("cancel")}
      </Button>
      <div className="w-px h-6 bg-border" />
      <Button variant="ghost" size="sm" onClick={() => openModal("shop")}>
        <ShoppingBag className="h-4 w-4" />
        {t("shop")}
      </Button>
    </div>
  );
}
