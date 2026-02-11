"use client";

import { useState } from "react";
import { Activity } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

const CONSENT_STORAGE_KEY = "focus-squad-input-tracking-consent";

export type ConsentValue = "granted" | "denied";

export function getStoredConsent(): ConsentValue | null {
  if (typeof window === "undefined") return null;
  const stored = localStorage.getItem(CONSENT_STORAGE_KEY);
  if (stored === "granted" || stored === "denied") return stored;
  return null;
}

function setStoredConsent(value: ConsentValue) {
  localStorage.setItem(CONSENT_STORAGE_KEY, value);
}

interface ActivityConsentPromptProps {
  onConsent: (granted: boolean) => void;
}

export function ActivityConsentPrompt({ onConsent }: ActivityConsentPromptProps) {
  const t = useTranslations("presence");
  const [visible, setVisible] = useState(() => getStoredConsent() === null);

  if (!visible) return null;

  const handleChoice = (granted: boolean) => {
    setStoredConsent(granted ? "granted" : "denied");
    setVisible(false);
    onConsent(granted);
  };

  return (
    <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-30 max-w-sm animate-in fade-in slide-in-from-bottom-4 duration-300">
      <div className="bg-card border border-border rounded-xl shadow-soft p-4 space-y-3">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-accent/20 p-2 shrink-0">
            <Activity className="h-4 w-4 text-accent" />
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">{t("activityPrompt")}</p>
        </div>
        <div className="flex gap-2 justify-end">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleChoice(false)}
            className="text-muted-foreground"
          >
            {t("noThanks")}
          </Button>
          <Button variant="default" size="sm" onClick={() => handleChoice(true)}>
            {t("enable")}
          </Button>
        </div>
      </div>
    </div>
  );
}
