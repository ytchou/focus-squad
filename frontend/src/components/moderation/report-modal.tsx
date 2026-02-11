"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { AlertTriangle, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { toast } from "sonner";

interface ReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportedUserId: string;
  reportedDisplayName: string;
  sessionId: string;
}

const MAX_DESCRIPTION_LENGTH = 2000;

export function ReportModal({
  isOpen,
  onClose,
  reportedUserId,
  reportedDisplayName,
  sessionId,
}: ReportModalProps) {
  const t = useTranslations("moderation");
  const tc = useTranslations("common");
  const [category, setCategory] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const reportCategories = [
    {
      value: "verbal_harassment",
      label: t("verbalHarassment"),
      description: t("verbalHarassmentDesc"),
    },
    {
      value: "explicit_content",
      label: t("explicitContent"),
      description: t("explicitContentDesc"),
    },
    {
      value: "threatening_behavior",
      label: t("threateningBehavior"),
      description: t("threateningBehaviorDesc"),
    },
    {
      value: "spam_scam",
      label: t("spamScam"),
      description: t("spamScamDesc"),
    },
    {
      value: "other",
      label: t("otherLabel"),
      description: t("otherDesc"),
    },
  ];

  const resetState = () => {
    setCategory(null);
    setDescription("");
    setIsSubmitting(false);
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const handleSubmit = async () => {
    if (!category) return;

    setIsSubmitting(true);
    try {
      await api.post("/moderation/reports", {
        reported_user_id: reportedUserId,
        session_id: sessionId,
        category,
        description: description.trim() || undefined,
      });
      toast.success(t("reportSubmittedToast"));
      handleClose();
    } catch {
      toast.error(t("reportFailedToast"));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="size-5 text-destructive" />
            {t("reportDisplayName", { name: reportedDisplayName })}
          </DialogTitle>
          <DialogDescription>{t("reportSelectReason")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          {reportCategories.map((cat) => (
            <label
              key={cat.value}
              className="flex items-start gap-3 rounded-lg border border-border p-3 cursor-pointer hover:bg-muted/50 transition-colors has-[:checked]:border-primary has-[:checked]:bg-primary/5"
            >
              <input
                type="radio"
                name="report-category"
                value={cat.value}
                checked={category === cat.value}
                onChange={() => setCategory(cat.value)}
                className="mt-0.5 accent-[hsl(var(--primary))]"
              />
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium text-foreground">{cat.label}</span>
                <p className="text-xs text-muted-foreground">{cat.description}</p>
              </div>
            </label>
          ))}
        </div>

        <div className="space-y-1.5">
          <label htmlFor="report-description" className="text-sm font-medium text-foreground">
            {t("additionalDetails")}
          </label>
          <textarea
            id="report-description"
            value={description}
            onChange={(e) => setDescription(e.target.value.slice(0, MAX_DESCRIPTION_LENGTH))}
            placeholder={t("additionalPlaceholder")}
            rows={3}
            className="w-full resize-none rounded-lg border border-border bg-input px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <p className="text-xs text-muted-foreground text-right">
            {description.length}/{MAX_DESCRIPTION_LENGTH}
          </p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isSubmitting}>
            {tc("cancel")}
          </Button>
          <Button variant="destructive" onClick={handleSubmit} disabled={!category || isSubmitting}>
            {isSubmitting && <Loader2 className="size-4 mr-2 animate-spin" />}
            {t("submitReport")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
