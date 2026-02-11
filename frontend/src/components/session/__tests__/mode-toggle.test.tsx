import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ModeToggle } from "../mode-toggle";

describe("ModeToggle", () => {
  it("renders Voice and Quiet buttons", () => {
    render(<ModeToggle mode="forced_audio" onChange={() => {}} />);
    expect(screen.getByText("Voice")).toBeInTheDocument();
    expect(screen.getByText("Quiet")).toBeInTheDocument();
  });

  it("highlights Voice when mode is forced_audio", () => {
    render(<ModeToggle mode="forced_audio" onChange={() => {}} />);
    expect(screen.getByText("Voice").closest("button")).toHaveClass("bg-primary");
    expect(screen.getByText("Quiet").closest("button")).not.toHaveClass("bg-accent");
  });

  it("highlights Quiet when mode is quiet", () => {
    render(<ModeToggle mode="quiet" onChange={() => {}} />);
    expect(screen.getByText("Quiet").closest("button")).toHaveClass("bg-accent");
    expect(screen.getByText("Voice").closest("button")).not.toHaveClass("bg-primary");
  });

  it("calls onChange with 'quiet' when Quiet clicked", () => {
    const onChange = vi.fn();
    render(<ModeToggle mode="forced_audio" onChange={onChange} />);
    fireEvent.click(screen.getByText("Quiet"));
    expect(onChange).toHaveBeenCalledWith("quiet");
  });

  it("calls onChange with 'forced_audio' when Voice clicked", () => {
    const onChange = vi.fn();
    render(<ModeToggle mode="quiet" onChange={onChange} />);
    fireEvent.click(screen.getByText("Voice"));
    expect(onChange).toHaveBeenCalledWith("forced_audio");
  });

  it("shows mode label", () => {
    render(<ModeToggle mode="forced_audio" onChange={() => {}} />);
    expect(screen.getByText("Table Mode:")).toBeInTheDocument();
  });
});
