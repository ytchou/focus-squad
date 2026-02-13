import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { InvitationAlert } from "../invitation-alert";
import type { InvitationInfo } from "@/stores";

const mockInvitation: InvitationInfo = {
  invitation_id: "inv-1",
  session_id: "session-1",
  inviter_id: "user-1",
  inviter_name: "Alice",
  session_start_time: "2026-02-13T14:00:00Z",
  session_mode: "quiet",
  status: "pending",
};

describe("InvitationAlert", () => {
  it("renders inviter name", () => {
    render(<InvitationAlert invitation={mockInvitation} onRespond={() => {}} />);
    // Translation includes the inviter name
    expect(screen.getByText(/Alice/)).toBeInTheDocument();
  });

  it("renders session time", () => {
    render(<InvitationAlert invitation={mockInvitation} onRespond={() => {}} />);
    // Should show "Session at" text with time
    expect(screen.getByText(/Session at/)).toBeInTheDocument();
  });

  it("shows accept button", () => {
    render(<InvitationAlert invitation={mockInvitation} onRespond={() => {}} />);
    expect(screen.getByText("Join")).toBeInTheDocument();
  });

  it("calls onRespond with accept=true when join clicked", () => {
    const onRespond = vi.fn();
    render(<InvitationAlert invitation={mockInvitation} onRespond={onRespond} />);

    fireEvent.click(screen.getByText("Join"));
    expect(onRespond).toHaveBeenCalledWith("session-1", "inv-1", true);
  });

  it("calls onRespond with accept=false when decline clicked", () => {
    const onRespond = vi.fn();
    render(<InvitationAlert invitation={mockInvitation} onRespond={onRespond} />);

    // Find the decline button (the X button without "Join" text)
    const buttons = screen.getAllByRole("button");
    const declineButton = buttons.find((b) => !b.textContent?.includes("Join"));
    fireEvent.click(declineButton!);

    expect(onRespond).toHaveBeenCalledWith("session-1", "inv-1", false);
  });
});
