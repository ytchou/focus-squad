"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Download, Copy, Check, Loader2, Share2 } from "lucide-react";
import { useUIStore } from "@/stores";
import {
  generateMilestoneCard,
  downloadMilestoneCard,
  copyMilestoneCardToClipboard,
} from "@/lib/room/generate-milestone-card";
import type { RoomSnapshot } from "@/stores/gamification-store";

export function MilestoneShareModal() {
  const t = useTranslations("timeline");
  const activeModal = useUIStore((s) => s.activeModal);
  const modalData = useUIStore((s) => s.modalData);
  const closeModal = useUIStore((s) => s.closeModal);
  const isOpen = activeModal === "milestoneShare";

  const snapshot = modalData?.snapshot as RoomSnapshot | undefined;

  const [cardImageUrl, setCardImageUrl] = useState<string | null>(null);
  const [cardBlob, setCardBlob] = useState<Blob | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [copied, setCopied] = useState(false);

  const generateCard = useCallback(async () => {
    if (!snapshot) return;
    setIsGenerating(true);
    try {
      const date = new Date(snapshot.created_at).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
      const result = await generateMilestoneCard({
        snapshotImageUrl: snapshot.image_url,
        milestoneLabel: t(`milestone.${snapshot.milestone_type}`),
        date,
        sessionCount: snapshot.session_count_at,
        diaryExcerpt: snapshot.diary_excerpt,
      });
      setCardImageUrl(result.dataUrl);
      setCardBlob(result.blob);
    } catch {
      // Generation failed
    } finally {
      setIsGenerating(false);
    }
  }, [snapshot, t]);

  useEffect(() => {
    if (isOpen && snapshot) {
      setCardImageUrl(null);
      setCardBlob(null);
      setCopied(false);
      generateCard();
    }
  }, [isOpen, snapshot, generateCard]);

  const handleDownload = () => {
    if (!cardBlob || !snapshot) return;
    const filename = `focus-squad-${snapshot.milestone_type}-${Date.now()}.png`;
    downloadMilestoneCard(cardBlob, filename);
  };

  const handleCopy = async () => {
    if (!cardBlob) return;
    const ok = await copyMilestoneCardToClipboard(cardBlob);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && closeModal()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Share2 className="h-5 w-5 text-accent" />
            {t("shareCard")}
          </DialogTitle>
          <DialogDescription>{t("shareCardDesc")}</DialogDescription>
        </DialogHeader>

        {/* Card preview */}
        <div className="rounded-lg border border-border overflow-hidden bg-muted/30">
          {isGenerating ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : cardImageUrl ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img src={cardImageUrl} alt="Milestone card preview" className="w-full" />
          ) : (
            <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
              {t("shareCardError")}
            </div>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          <Button variant="accent" className="flex-1" disabled={!cardBlob} onClick={handleDownload}>
            <Download className="h-4 w-4" />
            {t("download")}
          </Button>
          <Button variant="outline" className="flex-1" disabled={!cardBlob} onClick={handleCopy}>
            {copied ? (
              <>
                <Check className="h-4 w-4" />
                {t("copied")}
              </>
            ) : (
              <>
                <Copy className="h-4 w-4" />
                {t("copyClipboard")}
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
