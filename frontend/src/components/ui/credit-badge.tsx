"use client";

import { cn } from "@/lib/utils";
import { Coins } from "lucide-react";
import { useCountdown } from "@/hooks/use-countdown";

interface CreditBadgeProps {
  credits: number;
  maxCredits?: number;
  showIcon?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
  refreshDate?: string | null;
  onClick?: () => void;
}

export function CreditBadge({
  credits,
  maxCredits,
  showIcon = true,
  size = "md",
  className,
  refreshDate,
  onClick,
}: CreditBadgeProps) {
  const isZero = credits === 0;
  const isLow = credits === 1;
  const { countdown } = useCountdown(isZero ? (refreshDate ?? null) : null);

  const sizeClasses = {
    sm: "text-xs px-2 py-0.5 gap-1",
    md: "text-sm px-3 py-1 gap-1.5",
    lg: "text-base px-4 py-1.5 gap-2",
  };

  const iconSizes = {
    sm: "h-3 w-3",
    md: "h-4 w-4",
    lg: "h-5 w-5",
  };

  return (
    <div className="group relative">
      <div
        role={isZero ? "button" : undefined}
        tabIndex={isZero ? 0 : undefined}
        onClick={isZero ? onClick : undefined}
        onKeyDown={
          isZero
            ? (e) => {
                if (e.key === "Enter" || e.key === " ") onClick?.();
              }
            : undefined
        }
        className={cn(
          "inline-flex items-center rounded-full font-medium",
          "bg-accent/20 text-accent",
          isLow && "bg-warning/20 text-warning",
          isZero && "bg-destructive/20 text-destructive cursor-pointer",
          sizeClasses[size],
          className
        )}
      >
        {showIcon && <Coins className={iconSizes[size]} />}
        <span>
          {credits}
          {maxCredits !== undefined && <span className="text-muted-foreground">/{maxCredits}</span>}
        </span>
      </div>
      {/* Countdown tooltip on hover when zero */}
      {isZero && countdown !== "--" && (
        <div className="pointer-events-none absolute top-full left-1/2 mt-1 -translate-x-1/2 whitespace-nowrap rounded-md bg-foreground px-2 py-1 text-xs text-background opacity-0 transition-opacity group-hover:opacity-100">
          Refreshes in {countdown}
        </div>
      )}
    </div>
  );
}
