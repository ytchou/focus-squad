"use client";

import { useTranslations } from "next-intl";
import { PictureInPicture2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface PiPToggleButtonProps {
  isPiPActive: boolean;
  isPiPSupported: boolean;
  onToggle: () => void;
  isPixelMode?: boolean;
}

export function PiPToggleButton({
  isPiPActive,
  isPiPSupported,
  onToggle,
  isPixelMode,
}: PiPToggleButtonProps) {
  const t = useTranslations("session");

  if (!isPiPSupported) return null;

  return (
    <div className="flex flex-col items-center gap-1">
      <button
        onClick={onToggle}
        className={cn(
          "h-10 w-10 flex items-center justify-center transition-colors",
          isPixelMode ? "rounded-pixel shadow-pixel" : "rounded-xl",
          isPiPActive
            ? "bg-accent text-accent-foreground"
            : "bg-muted/60 text-muted-foreground hover:bg-muted"
        )}
        title={isPiPActive ? t("pipClose") : t("pipOpen")}
      >
        <PictureInPicture2 className="h-4 w-4" />
      </button>
      <span
        className={cn(
          "text-[10px] text-muted-foreground",
          isPixelMode && "font-pixel text-[0.4rem]"
        )}
      >
        {t("pipMini")}
      </span>
    </div>
  );
}
