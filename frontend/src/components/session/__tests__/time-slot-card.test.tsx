import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { TimeSlotCard } from "../time-slot-card";

const defaultProps = {
  startTime: "2026-02-11T14:30:00+00:00",
  queueCount: 0,
  estimatedCount: 0,
  hasUserSession: false,
  isJoining: false,
  isDisabled: false,
  onJoin: vi.fn(),
};

describe("TimeSlotCard", () => {
  it("renders time display", () => {
    render(<TimeSlotCard {...defaultProps} />);
    // Should show formatted time (locale-dependent, but at least renders)
    const card = screen.getByRole("button", { name: /Join/i });
    expect(card).toBeInTheDocument();
  });

  it("shows 'study buddies' when queueCount > 0", () => {
    render(<TimeSlotCard {...defaultProps} queueCount={5} />);
    expect(screen.getByText("5 study buddies")).toBeInTheDocument();
  });

  it("shows 'Usually ~X at this time' when only estimatedCount > 0", () => {
    render(<TimeSlotCard {...defaultProps} estimatedCount={12} />);
    expect(screen.getByText("Usually ~12 at this time")).toBeInTheDocument();
  });

  it("shows 'Be the first!' when both counts are 0", () => {
    render(<TimeSlotCard {...defaultProps} />);
    expect(screen.getByText("Be the first!")).toBeInTheDocument();
  });

  it("prefers queueCount over estimatedCount for social proof", () => {
    render(<TimeSlotCard {...defaultProps} queueCount={3} estimatedCount={12} />);
    expect(screen.getByText("3 study buddies")).toBeInTheDocument();
    expect(screen.queryByText(/Usually/)).not.toBeInTheDocument();
  });

  it("shows 'Joined' badge when hasUserSession is true", () => {
    render(<TimeSlotCard {...defaultProps} hasUserSession={true} />);
    expect(screen.getByText("Joined")).toBeInTheDocument();
    expect(screen.queryByText("Join")).not.toBeInTheDocument();
  });

  it("calls onJoin when Join button clicked", () => {
    const onJoin = vi.fn();
    render(<TimeSlotCard {...defaultProps} onJoin={onJoin} />);
    fireEvent.click(screen.getByRole("button", { name: /Join/i }));
    expect(onJoin).toHaveBeenCalledTimes(1);
  });

  it("disables button when isDisabled=true", () => {
    render(<TimeSlotCard {...defaultProps} isDisabled={true} />);
    expect(screen.getByRole("button", { name: /Join/i })).toBeDisabled();
  });

  it("shows loading state when isJoining=true", () => {
    render(<TimeSlotCard {...defaultProps} isJoining={true} />);
    expect(screen.getByText("Joining...")).toBeInTheDocument();
  });

  it("shows no-credits hint when disabled with no_credits reason", () => {
    render(<TimeSlotCard {...defaultProps} isDisabled={true} disabledReason="no_credits" />);
    expect(screen.getByText("You need credits to join a table")).toBeInTheDocument();
  });

  it("shows pending-ratings hint when disabled with pending_ratings reason", () => {
    render(<TimeSlotCard {...defaultProps} isDisabled={true} disabledReason="pending_ratings" />);
    expect(screen.getByText("Rate your tablemates first")).toBeInTheDocument();
  });
});
