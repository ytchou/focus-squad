"use client";

import { useTranslations } from "next-intl";
import { Mic, MicOff } from "lucide-react";
import { cn } from "@/lib/utils";

type TableMode = "forced_audio" | "quiet";

interface ModeToggleProps {
  mode: TableMode;
  onChange: (mode: TableMode) => void;
}

export function ModeToggle({ mode, onChange }: ModeToggleProps) {
  const t = useTranslations("findTable");

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-medium text-muted-foreground">{t("modeLabel")}:</span>
      <div className="inline-flex rounded-lg border border-border bg-muted/50 p-1">
        <button
          onClick={() => onChange("forced_audio")}
          className={cn(
            "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            mode === "forced_audio"
              ? "bg-primary text-primary-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          <Mic className="h-3.5 w-3.5" />
          {t("forcedAudio")}
        </button>
        <button
          onClick={() => onChange("quiet")}
          className={cn(
            "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            mode === "quiet"
              ? "bg-accent text-accent-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          <MicOff className="h-3.5 w-3.5" />
          {t("quietMode")}
        </button>
      </div>
    </div>
  );
}
