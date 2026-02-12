"use client";

import { cn } from "@/lib/utils";
import { Package } from "lucide-react";

interface RoomItemProps {
  name: string;
  imageUrl: string | null;
  gridX: number;
  gridY: number;
  sizeW: number;
  sizeH: number;
  rotation?: number;
  isSelected?: boolean;
  editMode?: boolean;
  onClick?: () => void;
}

export function RoomItem({
  name,
  imageUrl,
  gridX,
  gridY,
  sizeW,
  sizeH,
  rotation = 0,
  isSelected = false,
  editMode = false,
  onClick,
}: RoomItemProps) {
  const rotationDeg = rotation * 90;

  return (
    <div
      className={cn(
        "absolute transition-all duration-200 flex items-center justify-center",
        editMode && "cursor-pointer hover:ring-2 hover:ring-accent/50 rounded-lg",
        isSelected && "ring-2 ring-accent rounded-lg"
      )}
      style={{
        gridColumn: `${gridX + 1} / span ${sizeW}`,
        gridRow: `${gridY + 1} / span ${sizeH}`,
        transform: rotationDeg ? `rotate(${rotationDeg}deg)` : undefined,
      }}
      onClick={onClick}
      title={name}
    >
      {imageUrl ? (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={imageUrl}
          alt={name}
          className="w-full h-full object-contain p-1"
          draggable={false}
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center bg-muted/50 rounded-lg border border-border">
          <Package className="h-6 w-6 text-muted-foreground" />
        </div>
      )}
    </div>
  );
}
