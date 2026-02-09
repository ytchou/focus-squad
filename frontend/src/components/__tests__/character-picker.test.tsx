import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CharacterPicker } from "../character-picker";

describe("CharacterPicker", () => {
  it("renders all 8 character options", () => {
    render(<CharacterPicker onSelect={vi.fn()} />);
    const options = screen.getAllByRole("button");
    expect(options.length).toBe(8);
  });

  it("calls onSelect when a character is clicked", () => {
    const onSelect = vi.fn();
    render(<CharacterPicker onSelect={onSelect} />);
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[2]);
    expect(onSelect).toHaveBeenCalledWith("char-3");
  });

  it("highlights the selected character", () => {
    render(<CharacterPicker selectedId="char-5" onSelect={vi.fn()} />);
    const buttons = screen.getAllByRole("button");
    // The 5th button (index 4) should have a ring/highlight
    expect(buttons[4]).toHaveClass("ring-2");
  });

  it("shows character names", () => {
    render(<CharacterPicker onSelect={vi.fn()} />);
    expect(screen.getByText("Scholar")).toBeInTheDocument();
    expect(screen.getByText("Artist")).toBeInTheDocument();
    expect(screen.getByText("Coder")).toBeInTheDocument();
  });

  it("pre-selects provided selectedId", () => {
    const onSelect = vi.fn();
    render(<CharacterPicker selectedId="char-1" onSelect={onSelect} />);
    // Should show a visual selection indicator on char-1
    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toHaveClass("ring-2");
  });
});
