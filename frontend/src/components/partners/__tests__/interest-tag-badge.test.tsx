import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { InterestTagBadge } from "../interest-tag-badge";

describe("InterestTagBadge", () => {
  it("renders tag text from translation", () => {
    render(<InterestTagBadge tag="coding" />);
    // The mock useTranslations returns partners.tags.coding
    expect(screen.getByText("partners.tags.coding")).toBeInTheDocument();
  });

  it("renders with correct styling classes", () => {
    const { container } = render(<InterestTagBadge tag="design" />);
    const badge = container.querySelector("span");
    expect(badge).toHaveClass("rounded-full", "border", "bg-muted/50");
  });

  it("renders different tags correctly", () => {
    const { rerender } = render(<InterestTagBadge tag="writing" />);
    expect(screen.getByText("partners.tags.writing")).toBeInTheDocument();

    rerender(<InterestTagBadge tag="music" />);
    expect(screen.getByText("partners.tags.music")).toBeInTheDocument();
  });
});
