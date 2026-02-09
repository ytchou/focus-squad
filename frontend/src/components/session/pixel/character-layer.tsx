"use client";

import { CharacterSprite } from "./character-sprite";
import {
  PIXEL_ROOMS,
  PIXEL_CHARACTERS,
  DEFAULT_ROOM,
  DEFAULT_CHARACTER,
} from "@/config/pixel-rooms";
import { getCharacterState } from "@/lib/session/character-state";
import type { PresenceState } from "@/types/activity";

interface Participant {
  id: string;
  livekitIdentity: string | null;
  seatNumber: number;
  username: string | null;
  displayName: string | null;
  isAI: boolean;
  presenceState: PresenceState;
  isCurrentUser: boolean;
  pixelAvatarId?: string | null;
  isTyping?: boolean;
}

interface CharacterLayerProps {
  participants: Participant[];
  roomType: string;
  speakingParticipantIds: Set<string>;
}

export function CharacterLayer({
  participants,
  roomType,
  speakingParticipantIds,
}: CharacterLayerProps) {
  const room = PIXEL_ROOMS[roomType] ?? PIXEL_ROOMS[DEFAULT_ROOM];

  // Assign characters - use participant's selected avatar, or assign from pool
  const getCharacterId = (p: Participant): string => {
    if (p.pixelAvatarId && PIXEL_CHARACTERS[p.pixelAvatarId]) return p.pixelAvatarId;
    // Fallback: assign based on seat number
    const characterIds = Object.keys(PIXEL_CHARACTERS);
    return characterIds[(p.seatNumber - 1) % characterIds.length] || DEFAULT_CHARACTER;
  };

  return (
    <div className="absolute inset-0 z-10">
      {participants.map((participant) => {
        const deskIndex = participant.seatNumber - 1; // seats are 1-indexed
        if (deskIndex < 0 || deskIndex >= 4) return null;
        const position = room.deskPositions[deskIndex];

        const isSpeaking = !!(
          participant.livekitIdentity && speakingParticipantIds.has(participant.livekitIdentity)
        );

        const state = getCharacterState({
          presenceState: participant.presenceState,
          isSpeaking,
          isTyping: participant.isTyping ?? false,
        });

        return (
          <CharacterSprite
            key={participant.id}
            characterId={getCharacterId(participant)}
            state={state}
            deskPosition={position}
            displayName={
              participant.displayName ||
              participant.username ||
              (participant.isAI ? "AI Companion" : "Guest")
            }
            isGhosting={participant.presenceState === "ghosting"}
          />
        );
      })}
    </div>
  );
}
