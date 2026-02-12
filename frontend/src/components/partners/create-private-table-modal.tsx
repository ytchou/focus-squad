"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { Calendar, Users, Mic, VolumeX, Bot, ChevronRight, ChevronLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { api } from "@/lib/api/client";
import type { PartnerInfo } from "@/stores";

interface CreatePrivateTableModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  partners: PartnerInfo[];
}

type Step = "time" | "partners" | "configure" | "confirm";

function getUpcomingSlots(count: number): Date[] {
  const now = new Date();
  const slots: Date[] = [];
  const next = new Date(now);
  next.setSeconds(0, 0);

  if (next.getMinutes() < 30) {
    next.setMinutes(30);
  } else {
    next.setMinutes(0);
    next.setHours(next.getHours() + 1);
  }

  for (let i = 0; i < count; i++) {
    slots.push(new Date(next));
    next.setMinutes(next.getMinutes() + 30);
  }
  return slots;
}

export function CreatePrivateTableModal({
  open,
  onOpenChange,
  partners,
}: CreatePrivateTableModalProps) {
  const t = useTranslations("partners");

  const [step, setStep] = useState<Step>("time");
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [selectedPartners, setSelectedPartners] = useState<string[]>([]);
  const [mode, setMode] = useState<"forced_audio" | "quiet">("quiet");
  const [maxSeats, setMaxSeats] = useState(4);
  const [aiFill, setAiFill] = useState(true);
  const [topic, setTopic] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const slots = useMemo(() => getUpcomingSlots(6), []);

  const steps: Step[] = ["time", "partners", "configure", "confirm"];
  const currentIndex = steps.indexOf(step);

  const canProceed = () => {
    if (step === "time") return selectedSlot !== null;
    if (step === "partners") return selectedPartners.length > 0;
    return true;
  };

  const handleNext = () => {
    if (currentIndex < steps.length - 1) {
      setStep(steps[currentIndex + 1]);
    }
  };

  const handleBack = () => {
    if (currentIndex > 0) {
      setStep(steps[currentIndex - 1]);
    }
  };

  const togglePartner = (userId: string) => {
    setSelectedPartners((prev) =>
      prev.includes(userId)
        ? prev.filter((id) => id !== userId)
        : prev.length < maxSeats - 1
          ? [...prev, userId]
          : prev
    );
  };

  const handleCreate = async () => {
    if (!selectedSlot) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await api.post("/api/v1/sessions/create-private", {
        start_time: selectedSlot,
        invited_user_ids: selectedPartners,
        mode,
        max_seats: maxSeats,
        ai_fill: aiFill,
        topic: topic.trim() || null,
      });
      onOpenChange(false);
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("createError"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setStep("time");
    setSelectedSlot(null);
    setSelectedPartners([]);
    setMode("quiet");
    setMaxSeats(4);
    setAiFill(true);
    setTopic("");
    setError(null);
  };

  const formatSlotTime = (iso: string) => {
    return new Date(iso).toLocaleTimeString([], {
      hour: "numeric",
      minute: "2-digit",
    });
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        onOpenChange(value);
        if (!value) resetForm();
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("createPrivateTable")}</DialogTitle>
        </DialogHeader>

        <div className="flex items-center justify-center gap-2 py-2">
          {steps.map((s, i) => (
            <div
              key={s}
              className={cn(
                "h-1.5 flex-1 rounded-full transition-colors",
                i <= currentIndex ? "bg-accent" : "bg-muted"
              )}
            />
          ))}
        </div>

        <div className="min-h-[200px]">
          {step === "time" && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">{t("selectTimeSlot")}</p>
              <div className="grid grid-cols-3 gap-2">
                {slots.map((slot) => {
                  const iso = slot.toISOString();
                  return (
                    <button
                      key={iso}
                      onClick={() => setSelectedSlot(iso)}
                      className={cn(
                        "flex flex-col items-center gap-1 rounded-xl border p-3 transition-colors",
                        selectedSlot === iso
                          ? "border-accent bg-accent/10 text-accent"
                          : "border-border bg-card text-foreground hover:border-accent/50"
                      )}
                    >
                      <Calendar className="h-4 w-4" />
                      <span className="text-sm font-medium">{formatSlotTime(iso)}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {step === "partners" && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                {t("selectPartners", { max: maxSeats - 1 })}
              </p>
              {partners.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  {t("noPartnersYet")}
                </p>
              ) : (
                <div className="space-y-2">
                  {partners.map((partner) => {
                    const selected = selectedPartners.includes(partner.user_id);
                    const displayName = partner.display_name || partner.username;
                    return (
                      <button
                        key={partner.user_id}
                        onClick={() => togglePartner(partner.user_id)}
                        className={cn(
                          "flex w-full items-center gap-3 rounded-xl border p-3 transition-colors",
                          selected
                            ? "border-accent bg-accent/10"
                            : "border-border bg-card hover:border-accent/50"
                        )}
                      >
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/20 text-accent text-sm font-semibold">
                          {displayName.charAt(0).toUpperCase()}
                        </div>
                        <span className="flex-1 text-left text-sm font-medium text-foreground">
                          {displayName}
                        </span>
                        <div
                          className={cn(
                            "h-5 w-5 rounded-md border-2 transition-colors",
                            selected ? "border-accent bg-accent" : "border-muted"
                          )}
                        />
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {step === "configure" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <p className="text-sm font-medium text-foreground">{t("tableMode")}</p>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setMode("forced_audio")}
                    className={cn(
                      "flex items-center gap-2 rounded-xl border p-3 text-sm transition-colors",
                      mode === "forced_audio"
                        ? "border-accent bg-accent/10 text-accent"
                        : "border-border bg-card text-foreground hover:border-accent/50"
                    )}
                  >
                    <Mic className="h-4 w-4" />
                    {t("forcedAudio")}
                  </button>
                  <button
                    onClick={() => setMode("quiet")}
                    className={cn(
                      "flex items-center gap-2 rounded-xl border p-3 text-sm transition-colors",
                      mode === "quiet"
                        ? "border-accent bg-accent/10 text-accent"
                        : "border-border bg-card text-foreground hover:border-accent/50"
                    )}
                  >
                    <VolumeX className="h-4 w-4" />
                    {t("quietMode")}
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium text-foreground">{t("maxSeats")}</p>
                <div className="flex gap-2">
                  {[2, 3, 4].map((n) => (
                    <button
                      key={n}
                      onClick={() => {
                        setMaxSeats(n);
                        setSelectedPartners((prev) => prev.slice(0, n - 1));
                      }}
                      className={cn(
                        "flex items-center gap-1.5 rounded-xl border px-4 py-2 text-sm transition-colors",
                        maxSeats === n
                          ? "border-accent bg-accent/10 text-accent"
                          : "border-border bg-card text-foreground hover:border-accent/50"
                      )}
                    >
                      <Users className="h-3.5 w-3.5" />
                      {n}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={() => setAiFill(!aiFill)}
                className="flex w-full items-center gap-3 rounded-xl border border-border bg-card p-3 transition-colors hover:border-accent/50"
              >
                <Bot className="h-4 w-4 text-muted-foreground" />
                <span className="flex-1 text-left text-sm text-foreground">{t("aiFillEmpty")}</span>
                <div
                  className={cn(
                    "h-5 w-5 rounded-md border-2 transition-colors",
                    aiFill ? "border-accent bg-accent" : "border-muted"
                  )}
                />
              </button>

              <div className="space-y-2">
                <p className="text-sm font-medium text-foreground">{t("topicOptional")}</p>
                <Input
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder={t("topicPlaceholder")}
                  maxLength={100}
                />
              </div>
            </div>
          )}

          {step === "confirm" && (
            <div className="space-y-3">
              <p className="text-sm font-medium text-foreground">{t("reviewDetails")}</p>
              <div className="space-y-2 rounded-xl border border-border bg-muted/30 p-4 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t("time")}</span>
                  <span className="font-medium text-foreground">
                    {selectedSlot ? formatSlotTime(selectedSlot) : "-"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t("invitees")}</span>
                  <span className="font-medium text-foreground">
                    {selectedPartners.length} {t("partners")}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t("mode")}</span>
                  <span className="font-medium text-foreground">
                    {mode === "forced_audio" ? t("forcedAudio") : t("quietMode")}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t("seats")}</span>
                  <span className="font-medium text-foreground">{maxSeats}</span>
                </div>
                {topic && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t("topic")}</span>
                    <span className="font-medium text-foreground truncate max-w-[180px]">
                      {topic}
                    </span>
                  </div>
                )}
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
            </div>
          )}
        </div>

        <DialogFooter>
          {currentIndex > 0 && (
            <Button variant="outline" onClick={handleBack} disabled={isSubmitting}>
              <ChevronLeft className="h-4 w-4" />
              {t("back")}
            </Button>
          )}
          <div className="flex-1" />
          {step === "confirm" ? (
            <Button variant="accent" onClick={handleCreate} disabled={isSubmitting}>
              {isSubmitting ? t("creating") : t("createTable")}
            </Button>
          ) : (
            <Button variant="accent" onClick={handleNext} disabled={!canProceed()}>
              {t("next")}
              <ChevronRight className="h-4 w-4" />
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
