"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api/client";
import { useRoomStore } from "@/stores/room-store";
import { useGamificationStore } from "@/stores";
import { toast } from "sonner";
import type { VisitorResult } from "@/stores/room-store";

const COMPANION_EMOJI: Record<string, string> = {
  cat: "🐱",
  dog: "🐕",
  bunny: "🐰",
  hamster: "🐹",
  owl: "🦉",
  fox: "🦊",
  turtle: "🐢",
  raccoon: "🦝",
};

interface VisitorNotificationProps {
  visitor: VisitorResult;
  onDismiss: () => void;
}

export function VisitorNotification({ visitor, onDismiss }: VisitorNotificationProps) {
  const t = useTranslations("room");
  const fetchRoom = useRoomStore((s) => s.fetchRoom);
  const checkMilestones = useGamificationStore((s) => s.checkMilestones);
  const [isAdopting, setIsAdopting] = useState(false);

  const emoji = COMPANION_EMOJI[visitor.companion_type] || "🐾";

  const handleAdopt = async () => {
    setIsAdopting(true);
    try {
      await api.post("/api/v1/companions/adopt", {
        companion_type: visitor.companion_type,
      });
      toast.success(t("companionAdopted"));
      await fetchRoom();
      checkMilestones();
      onDismiss();
    } catch {
      toast.error(t("adoptError"));
    } finally {
      setIsAdopting(false);
    }
  };

  return (
    <Dialog open onOpenChange={(open) => !open && onDismiss()}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle className="text-center">✨ {t("visitorArrived")}</DialogTitle>
          <DialogDescription className="text-center">
            {t("visitorDesc", { type: t(`companion.${visitor.companion_type}`) })}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col items-center py-4">
          <div className="text-6xl animate-bounce" style={{ animationDuration: "2s" }}>
            {emoji}
          </div>
          <p className="mt-3 text-lg font-medium">{t(`companion.${visitor.companion_type}`)}</p>
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-col">
          <Button variant="accent" className="w-full" onClick={handleAdopt} disabled={isAdopting}>
            {isAdopting ? <Loader2 className="h-4 w-4 animate-spin" /> : t("adopt")}
          </Button>
          <Button variant="ghost" className="w-full" onClick={onDismiss}>
            {t("maybeLater")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
