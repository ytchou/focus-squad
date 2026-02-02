"use client";

import { cn } from "@/lib/utils";
import { Coins } from "lucide-react";

interface CreditBadgeProps {
  credits: number;
  maxCredits?: number;
  showIcon?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function CreditBadge({
  credits,
  maxCredits,
  showIcon = true,
  size = "md",
  className,
}: CreditBadgeProps) {
  const isLow = credits <= 1;

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
    <div
      className={cn(
        "inline-flex items-center rounded-full font-medium",
        "bg-accent/20 text-accent",
        isLow && "bg-warning/20 text-warning",
        sizeClasses[size],
        className
      )}
    >
      {showIcon && <Coins className={iconSizes[size]} />}
      <span>
        {credits}
        {maxCredits !== undefined && (
          <span className="text-muted-foreground">/{maxCredits}</span>
        )}
      </span>
    </div>
  );
}
