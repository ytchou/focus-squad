import type { SpriteState } from "@/components/session/pixel/character-sprite";
import type { PresenceState } from "@/types/activity";

export interface CharacterStateInput {
  presenceState: PresenceState;
  isSpeaking: boolean;
  isTyping: boolean;
}

/**
 * Determines the character animation state from presence/activity signals.
 *
 * Priority (highest to lowest):
 * 1. Ghosting — user has been inactive >5 min
 * 2. Away — user has been inactive 2-5 min
 * 3. Speaking — user is producing audio via LiveKit
 * 4. Typing — user has keyboard activity within 3s
 * 5. Working — default idle state
 */
export function getCharacterState(input: CharacterStateInput): SpriteState {
  if (input.presenceState === "ghosting") return "ghosting";
  if (input.presenceState === "away") return "away";
  if (input.isSpeaking) return "speaking";
  if (input.isTyping) return "typing";
  return "working";
}
