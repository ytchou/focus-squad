"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { AppShell } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Pencil, ShoppingBag, BookOpen, Loader2 } from "lucide-react";
import { useRoomStore } from "@/stores/room-store";
import { useShopStore } from "@/stores/shop-store";
import { useUIStore } from "@/stores";
import { RoomGrid } from "@/components/room/room-grid";
import { EditToolbar } from "@/components/room/edit-toolbar";
import { EssenceBadge } from "@/components/room/essence-badge";
import { VisitorNotification } from "@/components/room/visitor-notification";
import type { VisitorResult } from "@/stores/room-store";

export default function RoomPage() {
  const t = useTranslations("room");
  const roomData = useRoomStore((s) => s.roomData);
  const isLoading = useRoomStore((s) => s.isLoading);
  const editMode = useRoomStore((s) => s.editMode);
  const toggleEditMode = useRoomStore((s) => s.toggleEditMode);
  const fetchRoom = useRoomStore((s) => s.fetchRoom);
  const fetchBalance = useShopStore((s) => s.fetchBalance);
  const openModal = useUIStore((s) => s.openModal);

  const [pendingVisitor, setPendingVisitor] = useState<VisitorResult | null>(null);

  useEffect(() => {
    fetchRoom().then((data) => {
      if (data?.visitors && data.visitors.length > 0) {
        setPendingVisitor(data.visitors[0]);
      }
    });
    fetchBalance();
  }, [fetchRoom, fetchBalance]);

  const essenceBalance = roomData?.essence_balance ?? 0;
  const companions = roomData?.companions ?? [];
  const adoptedCount = companions.filter((c) => c.adopted_at).length;

  if (isLoading && !roomData) {
    return (
      <AppShell>
        <div className="flex items-center justify-center py-24">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-foreground">{t("title")}</h1>
            <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
          </div>
          <div className="flex items-center gap-2">
            <EssenceBadge balance={essenceBalance} />
            <span className="text-xs text-muted-foreground">🐾 {adoptedCount}/8</span>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-2">
          {editMode ? (
            <EditToolbar />
          ) : (
            <>
              <Button variant="outline" size="sm" onClick={toggleEditMode}>
                <Pencil className="h-4 w-4" />
                {t("editRoom")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => openModal("shop")}>
                <ShoppingBag className="h-4 w-4" />
                {t("shop")}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => openModal("companionGuide")}>
                <BookOpen className="h-4 w-4" />
                {t("companions")}
              </Button>
            </>
          )}
        </div>

        {/* Room grid */}
        <div className="rounded-xl border border-border overflow-hidden bg-card">
          <RoomGrid />
        </div>

        {/* Empty state hint */}
        {roomData && roomData.inventory.length === 0 && !editMode && (
          <div className="text-center py-6">
            <p className="text-muted-foreground text-sm">{t("emptyHint")}</p>
            <Button variant="accent" size="sm" className="mt-2" onClick={() => openModal("shop")}>
              <ShoppingBag className="h-4 w-4" />
              {t("visitShop")}
            </Button>
          </div>
        )}
      </div>

      {/* Visitor notification */}
      {pendingVisitor && (
        <VisitorNotification visitor={pendingVisitor} onDismiss={() => setPendingVisitor(null)} />
      )}
    </AppShell>
  );
}
