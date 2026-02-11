"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { CheckCircle, Star, Clock } from "lucide-react";
import type { SessionPhase } from "@/stores/session-store";

interface SessionEndModalProps {
  open: boolean;
  onClose: () => void;
  sessionId: string;
  phase: SessionPhase;
  focusMinutes?: number;
  essenceEarned?: boolean;
}

export function SessionEndModal({
  open,
  onClose,
  sessionId,
  phase,
  focusMinutes,
  essenceEarned,
}: SessionEndModalProps) {
  const router = useRouter();
  const t = useTranslations("sessionEnd");

  const isCompleted = phase === "completed";
  const isSocialPhase = phase === "social";

  const displayFocusMinutes = focusMinutes ?? 45;
  const displayEssence = essenceEarned ?? isCompleted;

  const handleViewSummary = () => {
    onClose();
    router.push(`/session/${sessionId}/end`);
  };

  const handleRateTablemates = () => {
    onClose();
    router.push(`/session/${sessionId}/end`);
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-success/20">
            {isCompleted ? (
              <CheckCircle className="h-8 w-8 text-success" />
            ) : (
              <Clock className="h-8 w-8 text-accent" />
            )}
          </div>
          <DialogTitle className="text-center text-xl">
            {isCompleted ? t("sessionComplete") : t("socialTime")}
          </DialogTitle>
          <DialogDescription className="text-center">
            {isCompleted ? t("sessionCompleteDesc") : t("socialTimeDesc")}
          </DialogDescription>
        </DialogHeader>

        {/* Stats Summary */}
        <div className="bg-muted rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{t("sessionDuration")}</span>
            <span className="font-medium">{t("durationValue")}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{t("focusTime")}</span>
            <span className="font-medium">
              {t("focusTimeMinutes", { minutes: displayFocusMinutes })}
            </span>
          </div>
          {displayEssence && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{t("essenceEarned")}</span>
              <span className="font-medium text-accent">{t("essenceEarnedValue")}</span>
            </div>
          )}
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-col">
          {isSocialPhase && (
            <Button variant="default" className="w-full" onClick={handleRateTablemates}>
              <Star className="h-4 w-4 mr-2" />
              {t("rateTablematesBtn")}
            </Button>
          )}
          <Button
            variant={isSocialPhase ? "outline" : "default"}
            className="w-full"
            onClick={handleViewSummary}
          >
            {isCompleted ? t("viewSummary") : t("continueSession")}
          </Button>
          {isSocialPhase && (
            <p className="text-xs text-muted-foreground text-center">{t("socialEndsNote")}</p>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
