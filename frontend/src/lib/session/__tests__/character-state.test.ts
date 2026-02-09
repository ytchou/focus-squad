import { describe, it, expect } from "vitest";
import { getCharacterState, type CharacterStateInput } from "../character-state";

describe("getCharacterState", () => {
  // Priority order: ghosting > away > speaking > typing > working

  it("returns 'working' when active with no other signals", () => {
    const input: CharacterStateInput = {
      presenceState: "active",
      isSpeaking: false,
      isTyping: false,
    };
    expect(getCharacterState(input)).toBe("working");
  });

  it("returns 'typing' when active and typing", () => {
    const input: CharacterStateInput = {
      presenceState: "active",
      isSpeaking: false,
      isTyping: true,
    };
    expect(getCharacterState(input)).toBe("typing");
  });

  it("returns 'speaking' when active and speaking", () => {
    const input: CharacterStateInput = {
      presenceState: "active",
      isSpeaking: true,
      isTyping: false,
    };
    expect(getCharacterState(input)).toBe("speaking");
  });

  it("returns 'speaking' over 'typing' when both are true (speaking has higher priority)", () => {
    const input: CharacterStateInput = {
      presenceState: "active",
      isSpeaking: true,
      isTyping: true,
    };
    expect(getCharacterState(input)).toBe("speaking");
  });

  it("returns 'away' regardless of speaking/typing", () => {
    const input: CharacterStateInput = {
      presenceState: "away",
      isSpeaking: true,
      isTyping: true,
    };
    expect(getCharacterState(input)).toBe("away");
  });

  it("returns 'ghosting' regardless of speaking/typing", () => {
    const input: CharacterStateInput = {
      presenceState: "ghosting",
      isSpeaking: true,
      isTyping: true,
    };
    expect(getCharacterState(input)).toBe("ghosting");
  });

  it("returns 'working' for 'grace' presenceState with no activity", () => {
    const input: CharacterStateInput = {
      presenceState: "grace",
      isSpeaking: false,
      isTyping: false,
    };
    // grace maps to working (grace is not a sprite state)
    expect(getCharacterState(input)).toBe("working");
  });

  it("returns 'speaking' for 'grace' presenceState when speaking", () => {
    const input: CharacterStateInput = {
      presenceState: "grace",
      isSpeaking: true,
      isTyping: false,
    };
    expect(getCharacterState(input)).toBe("speaking");
  });
});
