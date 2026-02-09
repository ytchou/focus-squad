"use client";

import { useEffect, useRef, useState } from "react";
import { PIXEL_CHARACTERS, DEFAULT_CHARACTER, type CharacterConfig } from "@/config/pixel-rooms";

export type SpriteState = "working" | "speaking" | "away";

const SPEAKING_DEBOUNCE_MS = 2000;

interface CharacterSpriteProps {
  characterId: string;
  state: SpriteState;
  deskPosition: { top: string; left: string };
  displayName: string;
}

export function CharacterSprite({
  characterId,
  state,
  deskPosition,
  displayName,
}: CharacterSpriteProps) {
  const [displayState, setDisplayState] = useState<SpriteState>(state);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevState = useRef<SpriteState>(state);

  const config: CharacterConfig =
    PIXEL_CHARACTERS[characterId] ?? PIXEL_CHARACTERS[DEFAULT_CHARACTER];

  // Speaking debounce: holds "speaking" display for 2s after audio stops.
  // setState in effect is intentional here - this is a debounce timer pattern.
  useEffect(() => {
    const wasSpeaking = prevState.current === "speaking";
    prevState.current = state;

    if (state === "speaking") {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
        debounceTimer.current = null;
      }
      // eslint-disable-next-line react-hooks/set-state-in-effect -- debounce pattern
      setDisplayState("speaking");
      return;
    }

    if (wasSpeaking) {
      debounceTimer.current = setTimeout(() => {
        setDisplayState(state);
        debounceTimer.current = null;
      }, SPEAKING_DEBOUNCE_MS);
      return;
    }

    setDisplayState(state);

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [state]);

  const stateConfig = config.states[displayState];
  const animationDuration = stateConfig.frames / stateConfig.fps;

  return (
    <div
      style={{
        position: "absolute",
        top: deskPosition.top,
        left: deskPosition.left,
        transform: "translate(-50%, -50%)",
      }}
      className="flex flex-col items-center"
    >
      <div
        data-state={displayState}
        data-character={config.id}
        className="image-rendering-pixelated"
        style={{
          width: config.frameWidth,
          height: config.frameHeight,
          backgroundImage: `url(${config.spriteSheet})`,
          backgroundRepeat: "no-repeat",
          backgroundPositionY: -(stateConfig.row * config.frameHeight),
          animation: `sprite-walk-${stateConfig.frames} ${animationDuration}s steps(${stateConfig.frames}) infinite`,
          imageRendering: "pixelated",
        }}
      />
      <span
        className="mt-1 text-center text-xs font-bold text-primary-foreground max-w-[80px] overflow-hidden text-ellipsis whitespace-nowrap"
        style={{ textShadow: "1px 1px 2px rgba(0,0,0,0.8)" }}
      >
        {displayName}
      </span>
    </div>
  );
}
