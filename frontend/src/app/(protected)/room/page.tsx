"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useTranslations } from "next-intl";
import { AppShell } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Pencil, ShoppingBag, BookOpen, Loader2, Clock } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRoomStore } from "@/stores/room-store";
import { useShopStore } from "@/stores/shop-store";
import { useUIStore, useGamificationStore } from "@/stores";
import { RoomGrid } from "@/components/room/room-grid";
import { EditToolbar } from "@/components/room/edit-toolbar";
import { EssenceBadge } from "@/components/room/essence-badge";
import { StreakProgressBar } from "@/components/room/streak-progress-bar";
import { VisitorNotification } from "@/components/room/visitor-notification";
import { GiftNotificationToast } from "@/components/room/gift-notification-toast";
import { captureRoomSnapshot } from "@/lib/room/capture-snapshot";
import { toast } from "sonner";
import { trackRoomViewed } from "@/lib/posthog/events";
import type { VisitorResult } from "@/stores/room-store";

export default function RoomPage() {
  const t = useTranslations("room");
  const router = useRouter();
  const roomData = useRoomStore((s) => s.roomData);
  const isLoading = useRoomStore((s) => s.isLoading);
  const editMode = useRoomStore((s) => s.editMode);
  const toggleEditMode = useRoomStore((s) => s.toggleEditMode);
  const fetchRoom = useRoomStore((s) => s.fetchRoom);
  const fetchBalance = useShopStore((s) => s.fetchBalance);
  const openModal = useUIStore((s) => s.openModal);
  const weeklyStreak = useGamificationStore((s) => s.weeklyStreak);
  const fetchStreak = useGamificationStore((s) => s.fetchStreak);
  const mood = useGamificationStore((s) => s.mood);
  const pendingReaction = useGamificationStore((s) => s.pendingReaction);
  const fetchMood = useGamificationStore((s) => s.fetchMood);
  const clearPendingReaction = useGamificationStore((s) => s.clearPendingReaction);
  const pendingMilestones = useGamificationStore((s) => s.pendingMilestones);
  const checkMilestones = useGamificationStore((s) => s.checkMilestones);
  const uploadSnapshot = useGamificationStore((s) => s.uploadSnapshot);

  const tTimeline = useTranslations("timeline");
  const roomGridRef = useRef<HTMLDivElement>(null);
  const [pendingVisitor, setPendingVisitor] = useState<VisitorResult | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);

  useEffect(() => {
    trackRoomViewed(true);
    fetchRoom().then((data) => {
      if (data?.visitors && data.visitors.length > 0) {
        setPendingVisitor(data.visitors[0]);
      }
    });
    fetchBalance();
    fetchStreak();
    fetchMood();
    checkMilestones();
  }, [fetchRoom, fetchBalance, fetchStreak, fetchMood, checkMilestones]);

  // Clear pending reaction after it plays (2.5s animation duration)
  useEffect(() => {
    if (pendingReaction) {
      const timer = setTimeout(() => {
        clearPendingReaction();
      }, 2500);
      return () => clearTimeout(timer);
    }
  }, [pendingReaction, clearPendingReaction]);

  // Capture room snapshot for pending milestones
  const captureMilestones = useCallback(async () => {
    if (isCapturing || pendingMilestones.length === 0 || !roomGridRef.current) return;
    setIsCapturing(true);
    try {
      const imageBase64 = await captureRoomSnapshot(roomGridRef.current);
      for (const milestone of pendingMilestones) {
        const result = await uploadSnapshot({
          milestone_type: milestone,
          image_base64: imageBase64,
        });
        if (result) {
          toast.success(
            tTimeline("newMilestone", {
              milestone: tTimeline(`milestone.${milestone}`),
            })
          );
        }
      }
    } catch {
      // Capture failure is non-critical
    } finally {
      setIsCapturing(false);
    }
  }, [isCapturing, pendingMilestones, uploadSnapshot, tTimeline]);

  useEffect(() => {
    if (pendingMilestones.length > 0 && roomGridRef.current && !isCapturing) {
      captureMilestones();
    }
  }, [pendingMilestones, captureMilestones, isCapturing]);

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

        {/* Weekly streak */}
        {weeklyStreak && (
          <StreakProgressBar
            sessionCount={weeklyStreak.session_count}
            nextBonusAt={weeklyStreak.next_bonus_at}
            bonus3Awarded={weeklyStreak.bonus_3_awarded}
            bonus5Awarded={weeklyStreak.bonus_5_awarded}
            compact
          />
        )}

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
              <Button variant="ghost" size="sm" onClick={() => router.push("/room/timeline")}>
                <Clock className="h-4 w-4" />
                {t("timeline")}
              </Button>
            </>
          )}
        </div>

        {/* Room grid */}
        <div ref={roomGridRef} className="rounded-xl border border-border overflow-hidden bg-card">
          <RoomGrid
            companionReaction={pendingReaction?.animation ?? null}
            companionMood={mood?.mood}
          />
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

      {/* Gift toast notifications */}
      <GiftNotificationToast />
    </AppShell>
  );
}
