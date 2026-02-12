"use client";

import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { useUIStore } from "@/stores";
import { useRoomStore } from "@/stores/room-store";
import { cn } from "@/lib/utils";
import type { CompanionInfo } from "@/stores/room-store";

const ALL_COMPANIONS = [
  { type: "cat", emoji: "🐱", starter: true },
  { type: "dog", emoji: "🐕", starter: true },
  { type: "bunny", emoji: "🐰", starter: true },
  { type: "hamster", emoji: "🐹", starter: true },
  { type: "owl", emoji: "🦉", starter: false, hint: "companionHint.owl" },
  { type: "fox", emoji: "🦊", starter: false, hint: "companionHint.fox" },
  { type: "turtle", emoji: "🐢", starter: false, hint: "companionHint.turtle" },
  { type: "raccoon", emoji: "🦝", starter: false, hint: "companionHint.raccoon" },
];

export function CompanionGuide() {
  const t = useTranslations("room");
  const activeModal = useUIStore((s) => s.activeModal);
  const closeModal = useUIStore((s) => s.closeModal);
  const isOpen = activeModal === "companionGuide";
  const companions = useRoomStore((s) => s.roomData?.companions || []);

  const isDiscovered = (type: string) =>
    companions.some((c: CompanionInfo) => c.companion_type === type);
  const isAdopted = (type: string) =>
    companions.some((c: CompanionInfo) => c.companion_type === type && c.adopted_at);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && closeModal()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">🐾 {t("companionGuide")}</DialogTitle>
          <DialogDescription>{t("companionGuideDesc")}</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-3">
          {ALL_COMPANIONS.map((comp) => {
            const discovered = isDiscovered(comp.type);
            const adopted = isAdopted(comp.type);

            return (
              <div
                key={comp.type}
                className={cn(
                  "rounded-xl border p-3 text-center transition-colors",
                  adopted
                    ? "border-success/30 bg-success/5"
                    : discovered
                      ? "border-accent/30 bg-accent/5"
                      : "border-border bg-muted/30"
                )}
              >
                <div className="text-3xl mb-1">
                  {discovered || comp.starter ? comp.emoji : "❓"}
                </div>
                <p className="text-sm font-medium">
                  {discovered || comp.starter ? t(`companion.${comp.type}`) : t("undiscovered")}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {adopted
                    ? t("adopted")
                    : discovered
                      ? t("visiting")
                      : comp.hint
                        ? t(comp.hint)
                        : t("chooseAsStarter")}
                </p>
              </div>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}
