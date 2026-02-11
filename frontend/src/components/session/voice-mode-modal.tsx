"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Mic, MicOff, Volume2, VolumeX, Check } from "lucide-react";
import { cn } from "@/lib/utils";

type VoiceMode = "forced_audio" | "quiet";

interface VoiceModeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (mode: VoiceMode) => void;
  isLoading?: boolean;
}

export function VoiceModeModal({
  isOpen,
  onClose,
  onSelect,
  isLoading = false,
}: VoiceModeModalProps) {
  const t = useTranslations("voiceMode");
  const tCommon = useTranslations("common");
  const [selectedMode, setSelectedMode] = useState<VoiceMode | null>(null);

  const handleConfirm = () => {
    if (selectedMode) {
      onSelect(selectedMode);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
          <DialogDescription>{t("subtitle")}</DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Forced Audio Option */}
          <button
            onClick={() => setSelectedMode("forced_audio")}
            disabled={isLoading}
            className={cn(
              "relative flex items-start gap-4 p-4 rounded-xl border-2 text-left transition-all",
              "hover:border-primary/50 hover:bg-primary/5",
              selectedMode === "forced_audio" ? "border-primary bg-primary/10" : "border-border"
            )}
          >
            <div
              className={cn(
                "flex h-12 w-12 shrink-0 items-center justify-center rounded-full",
                selectedMode === "forced_audio"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              )}
            >
              <Mic className="h-6 w-6" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-foreground flex items-center gap-2">
                {t("voiceMode")}
                {selectedMode === "forced_audio" && <Check className="h-4 w-4 text-primary" />}
              </h3>
              <p className="text-sm text-muted-foreground mt-1">{t("voiceModeDesc")}</p>
              <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                <Volume2 className="h-3 w-3" />
                <span>{t("voiceModeHint")}</span>
              </div>
            </div>
          </button>

          {/* Quiet Mode Option */}
          <button
            onClick={() => setSelectedMode("quiet")}
            disabled={isLoading}
            className={cn(
              "relative flex items-start gap-4 p-4 rounded-xl border-2 text-left transition-all",
              "hover:border-accent/50 hover:bg-accent/5",
              selectedMode === "quiet" ? "border-accent bg-accent/10" : "border-border"
            )}
          >
            <div
              className={cn(
                "flex h-12 w-12 shrink-0 items-center justify-center rounded-full",
                selectedMode === "quiet"
                  ? "bg-accent text-accent-foreground"
                  : "bg-muted text-muted-foreground"
              )}
            >
              <MicOff className="h-6 w-6" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-foreground flex items-center gap-2">
                {t("quietMode")}
                {selectedMode === "quiet" && <Check className="h-4 w-4 text-accent" />}
              </h3>
              <p className="text-sm text-muted-foreground mt-1">{t("quietModeDesc")}</p>
              <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                <VolumeX className="h-3 w-3" />
                <span>{t("quietModeHint")}</span>
              </div>
            </div>
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 justify-end">
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            {tCommon("cancel")}
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!selectedMode || isLoading}
            className={cn(
              selectedMode === "forced_audio" && "bg-primary hover:bg-primary/90",
              selectedMode === "quiet" && "bg-accent hover:bg-accent/90"
            )}
          >
            {isLoading ? t("matching") : t("joinTable")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
