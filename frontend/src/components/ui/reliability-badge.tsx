"use client";

import { cn } from "@/lib/utils";
import { Shield, ShieldCheck, ShieldAlert } from "lucide-react";

interface ReliabilityBadgeProps {
  score: number;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

type ReliabilityTier = "high" | "medium" | "low";

function getReliabilityTier(score: number): ReliabilityTier {
  if (score >= 80) return "high";
  if (score >= 50) return "medium";
  return "low";
}

function getReliabilityLabel(tier: ReliabilityTier): string {
  switch (tier) {
    case "high":
      return "Reliable";
    case "medium":
      return "Good";
    case "low":
      return "Building";
  }
}

export function ReliabilityBadge({
  score,
  showLabel = true,
  size = "md",
  className,
}: ReliabilityBadgeProps) {
  const tier = getReliabilityTier(score);

  const tierStyles = {
    high: "bg-success/20 text-success",
    medium: "bg-accent/20 text-accent",
    low: "bg-muted text-muted-foreground",
  };

  const TierIcon = {
    high: ShieldCheck,
    medium: Shield,
    low: ShieldAlert,
  }[tier];

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
        tierStyles[tier],
        sizeClasses[size],
        className
      )}
    >
      <TierIcon className={iconSizes[size]} />
      {showLabel && <span>{getReliabilityLabel(tier)}</span>}
      <span className="tabular-nums">{score}%</span>
    </div>
  );
}
