import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DiaryEntryCard } from "../diary-entry-card";
import type { DiaryEntry } from "@/lib/api/client";

const baseEntry: DiaryEntry = {
  session_id: "s-1",
  session_date: "2026-02-08T10:00:00+00:00",
  session_topic: "Deep Work Sprint",
  focus_minutes: 45,
  reflections: [
    { phase: "setup", content: "Ship the diary feature", created_at: "2026-02-08T10:01:00+00:00" },
    { phase: "break", content: "Going well so far", created_at: "2026-02-08T10:30:00+00:00" },
  ],
  note: null,
  tags: [],
};

const mockSaveNote = vi.fn().mockResolvedValue(undefined);

describe("DiaryEntryCard", () => {
  it("renders session topic and focus time", () => {
    render(<DiaryEntryCard entry={baseEntry} onSaveNote={mockSaveNote} />);
    expect(screen.getByText("Deep Work Sprint")).toBeInTheDocument();
    expect(screen.getByText("45 min")).toBeInTheDocument();
  });

  it("shows fallback title when no topic", () => {
    const noTopic = { ...baseEntry, session_topic: null };
    render(<DiaryEntryCard entry={noTopic} onSaveNote={mockSaveNote} />);
    expect(screen.getByText("Focus Session")).toBeInTheDocument();
  });

  it("shows essence indicator when focus_minutes >= 20", () => {
    render(<DiaryEntryCard entry={baseEntry} onSaveNote={mockSaveNote} />);
    expect(screen.getByText("+1 Essence")).toBeInTheDocument();
  });

  it("hides essence indicator when focus_minutes < 20", () => {
    const short = { ...baseEntry, focus_minutes: 15 };
    render(<DiaryEntryCard entry={short} onSaveNote={mockSaveNote} />);
    expect(screen.queryByText("+1 Essence")).not.toBeInTheDocument();
  });

  it("shows reflection count and expands on click", () => {
    render(<DiaryEntryCard entry={baseEntry} onSaveNote={mockSaveNote} />);
    const toggle = screen.getByText("2 Reflections");
    expect(toggle).toBeInTheDocument();

    // Reflections should be collapsed initially
    expect(screen.queryByText("Ship the diary feature")).not.toBeInTheDocument();

    // Expand
    fireEvent.click(toggle);
    expect(screen.getByText("Ship the diary feature")).toBeInTheDocument();
    expect(screen.getByText("Going well so far")).toBeInTheDocument();
  });

  it("shows singular 'Reflection' for one entry", () => {
    const single = { ...baseEntry, reflections: [baseEntry.reflections[0]] };
    render(<DiaryEntryCard entry={single} onSaveNote={mockSaveNote} />);
    expect(screen.getByText("1 Reflection")).toBeInTheDocument();
  });

  it("shows no-reflections placeholder when empty", () => {
    const empty = { ...baseEntry, reflections: [] };
    render(<DiaryEntryCard entry={empty} onSaveNote={mockSaveNote} />);
    expect(screen.getByText("No reflections this session")).toBeInTheDocument();
  });

  it("renders tags as badges", () => {
    const tagged = { ...baseEntry, tags: ["productive", "deep-focus"] };
    render(<DiaryEntryCard entry={tagged} onSaveNote={mockSaveNote} />);
    expect(screen.getByText("productive")).toBeInTheDocument();
    expect(screen.getByText("deep-focus")).toBeInTheDocument();
  });

  it("shows saved note text", () => {
    const noted = { ...baseEntry, note: "Great session today!" };
    render(<DiaryEntryCard entry={noted} onSaveNote={mockSaveNote} />);
    expect(screen.getByText("Great session today!")).toBeInTheDocument();
  });

  it("shows 'Add journal note' button when no note", () => {
    render(<DiaryEntryCard entry={baseEntry} onSaveNote={mockSaveNote} />);
    expect(screen.getByText("Add journal note")).toBeInTheDocument();
  });

  it("shows 'Edit note & tags' button when note exists", () => {
    const noted = { ...baseEntry, note: "Existing note" };
    render(<DiaryEntryCard entry={noted} onSaveNote={mockSaveNote} />);
    expect(screen.getByText("Edit note & tags")).toBeInTheDocument();
  });

  it("calls onSaveNote when saving journal editor", async () => {
    const saveFn = vi.fn().mockResolvedValue(undefined);
    render(<DiaryEntryCard entry={baseEntry} onSaveNote={saveFn} />);

    // Open editor
    fireEvent.click(screen.getByText("Add journal note"));

    // Type in the textarea
    const textarea = screen.getByPlaceholderText(/reflect on your session/i);
    fireEvent.change(textarea, { target: { value: "My note" } });

    // Save
    fireEvent.click(screen.getByText("Save"));

    await waitFor(() => {
      expect(saveFn).toHaveBeenCalledWith("s-1", "My note", []);
    });
  });
});
