"use client";

import { PIXEL_CHARACTERS, CHARACTER_IDS } from "@/config/pixel-rooms";
import { cn } from "@/lib/utils";

interface CharacterPickerProps {
  selectedId?: string | null;
  onSelect: (characterId: string) => void;
}

export function CharacterPicker({ selectedId, onSelect }: CharacterPickerProps) {
  return (
    <div className="grid grid-cols-4 gap-4">
      {CHARACTER_IDS.map((id) => {
        const char = PIXEL_CHARACTERS[id];
        const isSelected = selectedId === id;

        return (
          <button
            key={id}
            onClick={() => onSelect(id)}
            className={cn(
              "flex flex-col items-center gap-2 p-3 rounded-xl border-2 transition-all hover:scale-105",
              isSelected
                ? "border-primary ring-2 ring-primary/30 bg-primary/5"
                : "border-border hover:border-primary/50 bg-surface"
            )}
          >
            {/* Character sprite preview (working animation) */}
            <div
              className="w-16 h-16"
              style={{
                backgroundImage: `url(${char.spriteSheet})`,
                backgroundRepeat: "no-repeat",
                backgroundPositionY: -(char.states.working.row * char.frameHeight),
                animation: `sprite-walk-${char.states.working.frames} ${char.states.working.frames / char.states.working.fps}s steps(${char.states.working.frames}) infinite`,
                imageRendering: "pixelated",
              }}
            />
            <span className="text-xs font-medium text-foreground">{char.name}</span>
          </button>
        );
      })}
    </div>
  );
}
