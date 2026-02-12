"use client";

import { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { RoomPlacement } from "@/stores/room-store";

const COMPANION_EMOJI: Record<string, string> = {
  cat: "\uD83D\uDC31",
  dog: "\uD83D\uDC15",
  bunny: "\uD83D\uDC30",
  hamster: "\uD83D\uDC39",
  owl: "\uD83E\uDD89",
  fox: "\uD83E\uDD8A",
  turtle: "\uD83D\uDC22",
  raccoon: "\uD83E\uDD9D",
};

function computePosition(placements: RoomPlacement[], gridCellSize: number) {
  if (placements.length === 0) {
    return { x: 2 * gridCellSize, y: 1 * gridCellSize };
  }
  const target = placements[Math.floor(Math.random() * placements.length)];
  return {
    x: target.grid_x * gridCellSize + gridCellSize * 0.1,
    y: target.grid_y * gridCellSize + gridCellSize * 0.1,
  };
}

interface CompanionSpriteProps {
  companionType: string;
  placements: RoomPlacement[];
  gridCellSize: number;
  className?: string;
}

export function CompanionSprite({
  companionType,
  placements,
  gridCellSize,
  className,
}: CompanionSpriteProps) {
  const [position, setPosition] = useState(() => computePosition(placements, gridCellSize));
  const placementsRef = useRef(placements);
  const cellSizeRef = useRef(gridCellSize);

  useEffect(() => {
    placementsRef.current = placements;
    cellSizeRef.current = gridCellSize;
  });

  useEffect(() => {
    const interval = setInterval(
      () => {
        setPosition(computePosition(placementsRef.current, cellSizeRef.current));
      },
      30000 + Math.random() * 30000
    );
    return () => clearInterval(interval);
  }, []);

  const emoji = COMPANION_EMOJI[companionType] || "\uD83D\uDC3E";

  return (
    <div
      className={cn(
        "absolute transition-all duration-[2000ms] ease-in-out pointer-events-none z-10",
        className
      )}
      style={{
        left: position.x,
        top: position.y,
        width: gridCellSize * 0.8,
        height: gridCellSize * 0.8,
      }}
    >
      <div
        className="w-full h-full flex items-center justify-center text-2xl animate-bounce"
        style={{ animationDuration: "3s" }}
      >
        {emoji}
      </div>
    </div>
  );
}
