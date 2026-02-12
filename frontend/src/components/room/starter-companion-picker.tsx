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
import { useUIStore } from "@/stores";
import { api } from "@/lib/api/client";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const STARTERS = [
  { type: "cat", emoji: "🐱", personalityKey: "catPersonality" },
  { type: "dog", emoji: "🐕", personalityKey: "dogPersonality" },
  { type: "bunny", emoji: "🐰", personalityKey: "bunnyPersonality" },
  { type: "hamster", emoji: "🐹", personalityKey: "hamsterPersonality" },
];

interface StarterCompanionPickerProps {
  onComplete?: (companionType: string) => void;
}

export function StarterCompanionPicker({ onComplete }: StarterCompanionPickerProps) {
  const t = useTranslations("room");
  const activeModal = useUIStore((s) => s.activeModal);
  const closeModal = useUIStore((s) => s.closeModal);
  const isOpen = activeModal === "starterPicker";

  const [selected, setSelected] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChoose = async () => {
    if (!selected) return;
    setIsSubmitting(true);
    try {
      await api.post("/api/v1/companions/choose-starter", {
        companion_type: selected,
      });
      toast.success(t("starterChosen"));
      closeModal();
      onComplete?.(selected);
    } catch {
      toast.error(t("starterError"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && closeModal()}>
      <DialogContent className="sm:max-w-md" showCloseButton={false}>
        <DialogHeader>
          <DialogTitle className="text-center">🐾 {t("chooseCompanion")}</DialogTitle>
          <DialogDescription className="text-center">{t("chooseCompanionDesc")}</DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-3">
          {STARTERS.map((s) => (
            <button
              key={s.type}
              className={cn(
                "rounded-xl border-2 p-4 text-center transition-all",
                selected === s.type
                  ? "border-accent bg-accent/10 scale-105"
                  : "border-border hover:border-accent/50 hover:bg-accent/5"
              )}
              onClick={() => setSelected(s.type)}
            >
              <div className="text-4xl mb-2">{s.emoji}</div>
              <p className="text-sm font-medium">{t(`companion.${s.type}`)}</p>
              <p className="text-xs text-muted-foreground mt-1">{t(s.personalityKey)}</p>
            </button>
          ))}
        </div>

        <DialogFooter>
          <Button
            variant="accent"
            className="w-full"
            disabled={!selected || isSubmitting}
            onClick={handleChoose}
          >
            {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : t("adoptCompanion")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
