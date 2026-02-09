import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PiPMiniView } from "../pip-mini-view";
import { PHASE_LABELS, type PiPParticipant } from "../pip-colors";
import { formatTime } from "@/lib/session/phase-utils";
import type { SessionPhase } from "@/stores/session-store";

function makeParticipant(
  displayName: string | null,
  presenceState: PiPParticipant["presenceState"] = "active"
): PiPParticipant {
  return { displayName, presenceState };
}

describe("PiPMiniView", () => {
  // -------------------------------------------------------------------------
  // Timer formatting
  // -------------------------------------------------------------------------
  describe("timer display", () => {
    it("renders time formatted as MM:SS for 125 seconds", () => {
      render(<PiPMiniView phase="work1" timeRemaining={125} participants={[]} />);
      expect(screen.getByText("02:05")).toBeInTheDocument();
    });

    it("renders time formatted as MM:SS for 0 seconds", () => {
      render(<PiPMiniView phase="completed" timeRemaining={0} participants={[]} />);
      expect(screen.getByText("00:00")).toBeInTheDocument();
    });

    it("renders time formatted as MM:SS for 3599 seconds", () => {
      render(<PiPMiniView phase="work1" timeRemaining={3599} participants={[]} />);
      expect(screen.getByText("59:59")).toBeInTheDocument();
    });

    it("matches the formatTime utility output", () => {
      const seconds = 754;
      render(<PiPMiniView phase="work2" timeRemaining={seconds} participants={[]} />);
      expect(screen.getByText(formatTime(seconds))).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Phase label display
  // -------------------------------------------------------------------------
  describe("phase label", () => {
    const phases: SessionPhase[] = [
      "idle",
      "setup",
      "work1",
      "break",
      "work2",
      "social",
      "completed",
    ];

    it.each(phases)("renders correct label for phase '%s'", (phase) => {
      render(<PiPMiniView phase={phase} timeRemaining={60} participants={[]} />);
      expect(screen.getByText(PHASE_LABELS[phase])).toBeInTheDocument();
    });
  });

  // -------------------------------------------------------------------------
  // Participant rendering
  // -------------------------------------------------------------------------
  describe("participants", () => {
    it("renders up to 4 participant initials (uppercased first char)", () => {
      const participants: PiPParticipant[] = [
        makeParticipant("alice"),
        makeParticipant("Bob"),
        makeParticipant("charlie"),
        makeParticipant("Diana"),
      ];

      render(<PiPMiniView phase="work1" timeRemaining={300} participants={participants} />);

      expect(screen.getByText("A")).toBeInTheDocument();
      expect(screen.getByText("B")).toBeInTheDocument();
      expect(screen.getByText("C")).toBeInTheDocument();
      expect(screen.getByText("D")).toBeInTheDocument();
    });

    it("renders participant display names truncated to 8 characters", () => {
      const participants: PiPParticipant[] = [makeParticipant("Alexander"), makeParticipant("Bob")];

      render(<PiPMiniView phase="work1" timeRemaining={300} participants={participants} />);

      // "Alexander" truncated to 8 chars = "Alexande"
      expect(screen.getByText("Alexande")).toBeInTheDocument();
      expect(screen.getByText("Bob")).toBeInTheDocument();
    });

    it("handles null displayName gracefully by showing '?'", () => {
      const participants: PiPParticipant[] = [makeParticipant(null), makeParticipant("Bob")];

      render(<PiPMiniView phase="work1" timeRemaining={300} participants={participants} />);

      // The initial for null displayName should be "?"
      const questionMarks = screen.getAllByText("?");
      expect(questionMarks.length).toBeGreaterThanOrEqual(1);
    });

    it("renders 0 participants without errors", () => {
      const { container } = render(
        <PiPMiniView phase="work1" timeRemaining={300} participants={[]} />
      );

      // Should still render the overall container
      expect(container.firstChild).toBeInTheDocument();
      // Timer should still be present
      expect(screen.getByText("05:00")).toBeInTheDocument();
    });

    it("renders at most 4 participants even if more are provided", () => {
      const participants: PiPParticipant[] = [
        makeParticipant("Alice"),
        makeParticipant("Bob"),
        makeParticipant("Charlie"),
        makeParticipant("Diana"),
        makeParticipant("Eve"),
      ];

      render(<PiPMiniView phase="work1" timeRemaining={300} participants={participants} />);

      // First 4 initials should be present
      expect(screen.getByText("A")).toBeInTheDocument();
      expect(screen.getByText("B")).toBeInTheDocument();
      expect(screen.getByText("C")).toBeInTheDocument();
      expect(screen.getByText("D")).toBeInTheDocument();

      // 5th participant "Eve" should NOT render
      expect(screen.queryByText("Eve")).not.toBeInTheDocument();
    });
  });
});
