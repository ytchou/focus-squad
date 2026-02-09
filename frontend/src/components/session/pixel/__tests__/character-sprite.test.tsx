import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { CharacterSprite } from "../character-sprite";

describe("CharacterSprite", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders with display name", () => {
    render(
      <CharacterSprite
        characterId="char-1"
        state="working"
        deskPosition={{ top: "40%", left: "20%" }}
        displayName="Alice"
      />
    );
    expect(screen.getByText("Alice")).toBeInTheDocument();
  });

  it("positions at desk coordinates", () => {
    const { container } = render(
      <CharacterSprite
        characterId="char-1"
        state="working"
        deskPosition={{ top: "40%", left: "20%" }}
        displayName="Alice"
      />
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.style.top).toBe("40%");
    expect(wrapper.style.left).toBe("20%");
    expect(wrapper.style.position).toBe("absolute");
  });

  it("applies working state by default", () => {
    const { container } = render(
      <CharacterSprite
        characterId="char-1"
        state="working"
        deskPosition={{ top: "40%", left: "20%" }}
        displayName="Alice"
      />
    );
    const sprite = container.querySelector("[data-state='working']");
    expect(sprite).toBeInTheDocument();
  });

  it("applies speaking state", () => {
    const { container } = render(
      <CharacterSprite
        characterId="char-1"
        state="speaking"
        deskPosition={{ top: "40%", left: "20%" }}
        displayName="Alice"
      />
    );
    const sprite = container.querySelector("[data-state='speaking']");
    expect(sprite).toBeInTheDocument();
  });

  it("applies away state", () => {
    const { container } = render(
      <CharacterSprite
        characterId="char-1"
        state="away"
        deskPosition={{ top: "40%", left: "20%" }}
        displayName="Alice"
      />
    );
    const sprite = container.querySelector("[data-state='away']");
    expect(sprite).toBeInTheDocument();
  });

  it("debounces speaking state for 2 seconds", () => {
    const { container, rerender } = render(
      <CharacterSprite
        characterId="char-1"
        state="speaking"
        deskPosition={{ top: "40%", left: "20%" }}
        displayName="Alice"
      />
    );

    // Switch to working - should still show speaking due to debounce
    rerender(
      <CharacterSprite
        characterId="char-1"
        state="working"
        deskPosition={{ top: "40%", left: "20%" }}
        displayName="Alice"
      />
    );

    // Should still be speaking within debounce window
    expect(container.querySelector("[data-state='speaking']")).toBeInTheDocument();

    // After 2 seconds, should switch to working
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(container.querySelector("[data-state='working']")).toBeInTheDocument();
  });

  it("cancels debounce when speaking resumes", () => {
    const { container, rerender } = render(
      <CharacterSprite
        characterId="char-1"
        state="speaking"
        deskPosition={{ top: "40%", left: "20%" }}
        displayName="Alice"
      />
    );

    // Switch to working
    rerender(
      <CharacterSprite
        characterId="char-1"
        state="working"
        deskPosition={{ top: "40%", left: "20%" }}
        displayName="Alice"
      />
    );

    // Before debounce expires, resume speaking
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    rerender(
      <CharacterSprite
        characterId="char-1"
        state="speaking"
        deskPosition={{ top: "40%", left: "20%" }}
        displayName="Alice"
      />
    );

    // After original debounce would have expired, should still be speaking
    act(() => {
      vi.advanceTimersByTime(1500);
    });

    expect(container.querySelector("[data-state='speaking']")).toBeInTheDocument();
  });

  it("uses correct sprite sheet for character", () => {
    const { container } = render(
      <CharacterSprite
        characterId="char-3"
        state="working"
        deskPosition={{ top: "40%", left: "20%" }}
        displayName="Coder"
      />
    );
    const sprite = container.querySelector("[data-character='char-3']");
    expect(sprite).toBeInTheDocument();
  });

  it("falls back to default character for unknown ID", () => {
    render(
      <CharacterSprite
        characterId="unknown-char"
        state="working"
        deskPosition={{ top: "40%", left: "20%" }}
        displayName="Unknown"
      />
    );
    // Should still render without crashing
    expect(screen.getByText("Unknown")).toBeInTheDocument();
  });
});
