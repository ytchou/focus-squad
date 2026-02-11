"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { ShieldCheck, Shield, ShieldAlert, User } from "lucide-react";

interface ReliabilityBadgeProps {
  score: number;
  ratingCount?: number;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

type ReliabilityTier = "trusted" | "good" | "fair" | "new";

function getReliabilityTier(score: number, ratingCount?: number): ReliabilityTier {
  if (ratingCount !== undefined && ratingCount < 5) return "new";
  if (score >= 95) return "trusted";
  if (score >= 80) return "good";
  return "fair";
}

const TIER_LABEL_KEYS: Record<ReliabilityTier, string> = {
  trusted: "reliabilityTrusted",
  good: "reliabilityGood",
  fair: "reliabilityFair",
  new: "reliabilityNew",
};

export function ReliabilityBadge({
  score,
  ratingCount,
  showLabel = true,
  size = "md",
  className,
}: ReliabilityBadgeProps) {
  const t = useTranslations("rating");
  const tier = getReliabilityTier(score, ratingCount);

  const tierStyles = {
    trusted: "bg-success/20 text-success",
    good: "bg-accent/20 text-accent",
    fair: "bg-warning/20 text-warning",
    new: "bg-muted text-muted-foreground",
  };

  const TierIcon = {
    trusted: ShieldCheck,
    good: Shield,
    fair: ShieldAlert,
    new: User,
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
      {showLabel && <span>{t(TIER_LABEL_KEYS[tier])}</span>}
      {tier !== "new" && <span className="tabular-nums">{score}%</span>}
    </div>
  );
}
