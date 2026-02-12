"use client";

import { cn } from "@/lib/utils";

interface RoomBackgroundProps {
  roomType: string;
  className?: string;
}

const roomStyles: Record<string, { bg: string; pattern: string }> = {
  starter: {
    bg: "bg-surface",
    pattern:
      "bg-[radial-gradient(circle_at_50%_50%,_var(--border)_1px,_transparent_1px)] bg-[length:24px_24px]",
  },
  study_loft: {
    bg: "bg-card",
    pattern:
      "bg-[linear-gradient(45deg,_var(--border)_25%,_transparent_25%,_transparent_75%,_var(--border)_75%)] bg-[length:16px_16px]",
  },
  rooftop_garden: {
    bg: "bg-success/5",
    pattern:
      "bg-[radial-gradient(circle_at_50%_50%,_var(--success)_0.5px,_transparent_0.5px)] bg-[length:20px_20px] opacity-30",
  },
  cozy_cabin: {
    bg: "bg-accent/5",
    pattern: "bg-[linear-gradient(0deg,_var(--border)_1px,_transparent_1px)] bg-[length:100%_24px]",
  },
};

export function RoomBackground({ roomType, className }: RoomBackgroundProps) {
  const style = roomStyles[roomType] || roomStyles.starter;

  return (
    <div className={cn("absolute inset-0 rounded-xl overflow-hidden", style.bg, className)}>
      <div className={cn("absolute inset-0", style.pattern)} />
    </div>
  );
}
