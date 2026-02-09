import React from "react";
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { RoomAmbientAnimation } from "../room-ambient-animation";

describe("RoomAmbientAnimation", () => {
  it("renders lamp glow for cozy-study", () => {
    const { container } = render(<RoomAmbientAnimation roomType="cozy-study" />);
    const el = container.querySelector(".ambient-lamp");
    expect(el).toBeInTheDocument();
  });

  it("renders 3 steam wisps for coffee-shop", () => {
    const { container } = render(<RoomAmbientAnimation roomType="coffee-shop" />);
    const wisps = container.querySelectorAll(".ambient-steam-wisp");
    expect(wisps).toHaveLength(3);
  });

  it("renders rain streaks for library", () => {
    const { container } = render(<RoomAmbientAnimation roomType="library" />);
    const el = container.querySelector(".ambient-rain");
    expect(el).toBeInTheDocument();
  });

  it("returns null for unknown room type", () => {
    const { container } = render(<RoomAmbientAnimation roomType="unknown-room" />);
    expect(container.firstChild).toBeNull();
  });
});
