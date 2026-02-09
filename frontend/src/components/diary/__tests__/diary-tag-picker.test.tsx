import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DiaryTagPicker } from "../diary-tag-picker";

describe("DiaryTagPicker", () => {
  const ALL_TAGS = [
    "productive",
    "distracted",
    "breakthrough",
    "tired",
    "energized",
    "social",
    "deep-focus",
    "struggled",
  ];

  it("renders all 8 predefined tags", () => {
    render(<DiaryTagPicker selectedTags={[]} onChange={() => {}} />);
    for (const tag of ALL_TAGS) {
      expect(screen.getByText(tag)).toBeInTheDocument();
    }
  });

  it("highlights selected tags with primary style", () => {
    render(<DiaryTagPicker selectedTags={["productive", "tired"]} onChange={() => {}} />);
    const productive = screen.getByText("productive");
    const tired = screen.getByText("tired");
    const distracted = screen.getByText("distracted");

    expect(productive).toHaveClass("bg-primary");
    expect(tired).toHaveClass("bg-primary");
    expect(distracted).toHaveClass("bg-muted");
  });

  it("adds tag when clicking unselected tag", () => {
    const onChange = vi.fn();
    render(<DiaryTagPicker selectedTags={["productive"]} onChange={onChange} />);

    fireEvent.click(screen.getByText("tired"));
    expect(onChange).toHaveBeenCalledWith(["productive", "tired"]);
  });

  it("removes tag when clicking selected tag", () => {
    const onChange = vi.fn();
    render(<DiaryTagPicker selectedTags={["productive", "tired"]} onChange={onChange} />);

    fireEvent.click(screen.getByText("productive"));
    expect(onChange).toHaveBeenCalledWith(["tired"]);
  });

  it("shows section label", () => {
    render(<DiaryTagPicker selectedTags={[]} onChange={() => {}} />);
    expect(screen.getByText("Session tags")).toBeInTheDocument();
  });
});
