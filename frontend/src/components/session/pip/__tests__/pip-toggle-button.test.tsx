import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { PiPToggleButton } from "../pip-toggle-button";

describe("PiPToggleButton", () => {
  // -------------------------------------------------------------------------
  // Visibility
  // -------------------------------------------------------------------------
  it("returns null when isPiPSupported is false", () => {
    const { container } = render(
      <PiPToggleButton isPiPActive={false} isPiPSupported={false} onToggle={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders a button when isPiPSupported is true", () => {
    render(<PiPToggleButton isPiPActive={false} isPiPSupported={true} onToggle={vi.fn()} />);
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Title attribute
  // -------------------------------------------------------------------------
  it("shows 'Close Mini View' title when isPiPActive is true", () => {
    render(<PiPToggleButton isPiPActive={true} isPiPSupported={true} onToggle={vi.fn()} />);
    expect(screen.getByTitle("Close Mini View")).toBeInTheDocument();
  });

  it("shows 'Open Mini View' title when isPiPActive is false", () => {
    render(<PiPToggleButton isPiPActive={false} isPiPSupported={true} onToggle={vi.fn()} />);
    expect(screen.getByTitle("Open Mini View")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Click behavior
  // -------------------------------------------------------------------------
  it("calls onToggle when clicked", () => {
    const onToggle = vi.fn();
    render(<PiPToggleButton isPiPActive={false} isPiPSupported={true} onToggle={onToggle} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  // -------------------------------------------------------------------------
  // Label text
  // -------------------------------------------------------------------------
  it("shows 'Mini' label text", () => {
    render(<PiPToggleButton isPiPActive={false} isPiPSupported={true} onToggle={vi.fn()} />);
    expect(screen.getByText("Mini")).toBeInTheDocument();
  });
});
