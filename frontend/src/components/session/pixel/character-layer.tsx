"use client";

import { CharacterSprite, type SpriteState } from "./character-sprite";
import {
  PIXEL_ROOMS,
  PIXEL_CHARACTERS,
  DEFAULT_ROOM,
  DEFAULT_CHARACTER,
} from "@/config/pixel-rooms";

interface Participant {
  id: string;
  livekitIdentity: string | null;
  seatNumber: number;
  username: string | null;
  displayName: string | null;
  isAI: boolean;
  isActive: boolean;
  isCurrentUser: boolean;
  pixelAvatarId?: string | null;
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

  // Determine state for each participant
  const getState = (p: Participant): SpriteState => {
    if (!p.isActive) return "away";
    if (p.livekitIdentity && speakingParticipantIds.has(p.livekitIdentity)) return "speaking";
    return "working";
  };

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

        return (
          <CharacterSprite
            key={participant.id}
            characterId={getCharacterId(participant)}
            state={getState(participant)}
            deskPosition={position}
            displayName={
              participant.displayName ||
              participant.username ||
              (participant.isAI ? "AI Companion" : "Guest")
            }
          />
        );
      })}
    </div>
  );
}
