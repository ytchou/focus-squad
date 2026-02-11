"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { ThumbsUp, ThumbsDown, Minus } from "lucide-react";
import { RatingReasonsPicker } from "./rating-reasons-picker";

type RatingValue = "green" | "red" | "skip";

interface RatingCardProps {
  userId: string;
  username: string;
  displayName: string | null;
  avatarConfig: Record<string, unknown>;
  currentRating: RatingValue | null;
  reasons: string[];
  otherReasonText: string;
  onRatingChange: (value: RatingValue) => void;
  onReasonsChange: (reasons: string[]) => void;
  onOtherTextChange: (text: string) => void;
}

function getInitials(displayName: string | null, username: string): string {
  const name = displayName || username;
  return name
    .split(/\s+/)
    .map((word) => word[0])
    .filter(Boolean)
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function getAvatarColor(username: string): string {
  let hash = 0;
  for (let i = 0; i < username.length; i++) {
    hash = username.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash) % 360;
  return `hsl(${hue}, 35%, 55%)`;
}

export function RatingCard({
  userId: _userId,
  username,
  displayName,
  avatarConfig,
  currentRating,
  reasons,
  otherReasonText,
  onRatingChange,
  onReasonsChange,
  onOtherTextChange,
}: RatingCardProps) {
  const t = useTranslations("ratingCard");
  const initials = getInitials(displayName, username);
  const avatarColor =
    typeof avatarConfig.color === "string" ? avatarConfig.color : getAvatarColor(username);

  const ratingButtons: {
    value: RatingValue;
    label: string;
    icon: typeof ThumbsUp;
    selectedClass: string;
    unselectedClass: string;
  }[] = [
    {
      value: "green",
      label: t("goodPartner"),
      icon: ThumbsUp,
      selectedClass: "bg-success text-success-foreground border-success",
      unselectedClass:
        "bg-card text-muted-foreground border-border hover:bg-success/10 hover:text-success hover:border-success/40",
    },
    {
      value: "red",
      label: t("hadIssues"),
      icon: ThumbsDown,
      selectedClass: "bg-destructive text-destructive-foreground border-destructive",
      unselectedClass:
        "bg-card text-muted-foreground border-border hover:bg-destructive/10 hover:text-destructive hover:border-destructive/40",
    },
    {
      value: "skip",
      label: t("cantSay"),
      icon: Minus,
      selectedClass: "bg-muted text-foreground border-muted-foreground/30",
      unselectedClass:
        "bg-card text-muted-foreground border-border hover:bg-muted hover:text-foreground",
    },
  ];

  return (
    <div
      className={cn(
        "rounded-xl border bg-card p-4 shadow-sm",
        "transition-shadow duration-200",
        currentRating !== null && "shadow-md"
      )}
    >
      {/* User info */}
      <div className="flex items-center gap-3 mb-4">
        <div
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-white"
          style={{ backgroundColor: avatarColor }}
        >
          {initials}
        </div>
        <div className="min-w-0">
          <p className="font-medium text-foreground truncate">{displayName || username}</p>
          {displayName && <p className="text-xs text-muted-foreground truncate">@{username}</p>}
        </div>
      </div>

      {/* Rating buttons */}
      <div className="grid grid-cols-3 gap-2">
        {ratingButtons.map(({ value, label, icon: Icon, selectedClass, unselectedClass }) => {
          const isSelected = currentRating === value;
          return (
            <button
              key={value}
              type="button"
              onClick={() => onRatingChange(value)}
              className={cn(
                "flex flex-col items-center gap-1.5 rounded-lg border px-2 py-3",
                "text-xs font-medium transition-all duration-150",
                "focus:outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
                isSelected ? selectedClass : unselectedClass
              )}
            >
              <Icon className="h-5 w-5" />
              <span>{label}</span>
            </button>
          );
        })}
      </div>

      {/* Expandable reasons picker for red ratings */}
      {currentRating === "red" && (
        <RatingReasonsPicker
          reasons={reasons}
          otherText={otherReasonText}
          onReasonsChange={onReasonsChange}
          onOtherTextChange={onOtherTextChange}
        />
      )}
    </div>
  );
}
