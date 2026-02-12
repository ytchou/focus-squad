"use client";

import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface EssenceBadgeProps {
  balance: number;
  size?: "sm" | "md" | "lg";
  className?: string;
  onClick?: () => void;
}

export function EssenceBadge({ balance, size = "md", className, onClick }: EssenceBadgeProps) {
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
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") onClick();
            }
          : undefined
      }
      className={cn(
        "inline-flex items-center rounded-full font-medium",
        "bg-warning/20 text-warning",
        onClick && "cursor-pointer hover:bg-warning/30 transition-colors",
        sizeClasses[size],
        className
      )}
    >
      <Sparkles className={iconSizes[size]} />
      <span>{balance}</span>
    </div>
  );
}
