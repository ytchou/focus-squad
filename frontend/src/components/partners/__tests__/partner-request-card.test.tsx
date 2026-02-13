import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { PartnerRequestCard } from "../partner-request-card";
import type { PartnerRequestInfo } from "@/stores";

const createMockRequest = (overrides?: Partial<PartnerRequestInfo>): PartnerRequestInfo => ({
  partnership_id: "partnership-123",
  user_id: "user-456",
  username: "studybuddy",
  display_name: "Study Buddy",
  avatar_config: {},
  pixel_avatar_id: null,
  direction: "incoming",
  created_at: new Date().toISOString(),
  ...overrides,
});

describe("PartnerRequestCard", () => {
  const mockOnRespond = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders requester display name", () => {
    const request = createMockRequest({ display_name: "Focus Friend" });
    render(<PartnerRequestCard request={request} onRespond={mockOnRespond} />);

    expect(screen.getByText("Focus Friend")).toBeInTheDocument();
  });

  it("renders avatar initial", () => {
    const request = createMockRequest({ display_name: "Jane Doe" });
    render(<PartnerRequestCard request={request} onRespond={mockOnRespond} />);

    // Initial is first character of display name, uppercased
    expect(screen.getByText("J")).toBeInTheDocument();
  });

  it("shows 'wants to be partner' for incoming requests", () => {
    const request = createMockRequest({ direction: "incoming" });
    render(<PartnerRequestCard request={request} onRespond={mockOnRespond} />);

    // partners.wantsToBePartner = "wants to be your partner"
    expect(screen.getByText("wants to be your partner")).toBeInTheDocument();
  });

  it("shows 'pending request' for outgoing requests", () => {
    const request = createMockRequest({ direction: "outgoing" });
    render(<PartnerRequestCard request={request} onRespond={mockOnRespond} />);

    // partners.pendingRequest = "Request pending"
    expect(screen.getByText("Request pending")).toBeInTheDocument();
  });

  it("shows accept/decline buttons for incoming requests", () => {
    const request = createMockRequest({ direction: "incoming" });
    render(<PartnerRequestCard request={request} onRespond={mockOnRespond} />);

    // partners.accept = "Accept"
    // partners.decline = "Decline"
    expect(screen.getByRole("button", { name: /Accept/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Decline/i })).toBeInTheDocument();
  });

  it("shows cancel button for outgoing requests", () => {
    const request = createMockRequest({ direction: "outgoing" });
    render(<PartnerRequestCard request={request} onRespond={mockOnRespond} />);

    // partners.cancel = "Cancel Request"
    expect(screen.getByRole("button", { name: /Cancel Request/i })).toBeInTheDocument();
  });

  it("calls onRespond with accept=true when accept clicked", () => {
    const request = createMockRequest({
      partnership_id: "partnership-abc",
      direction: "incoming",
    });
    render(<PartnerRequestCard request={request} onRespond={mockOnRespond} />);

    fireEvent.click(screen.getByRole("button", { name: /Accept/i }));

    expect(mockOnRespond).toHaveBeenCalledWith("partnership-abc", true);
  });

  it("calls onRespond with accept=false when decline clicked", () => {
    const request = createMockRequest({
      partnership_id: "partnership-xyz",
      direction: "incoming",
    });
    render(<PartnerRequestCard request={request} onRespond={mockOnRespond} />);

    fireEvent.click(screen.getByRole("button", { name: /Decline/i }));

    expect(mockOnRespond).toHaveBeenCalledWith("partnership-xyz", false);
  });

  it("calls onRespond with accept=false when cancel clicked", () => {
    const request = createMockRequest({
      partnership_id: "partnership-cancel",
      direction: "outgoing",
    });
    render(<PartnerRequestCard request={request} onRespond={mockOnRespond} />);

    fireEvent.click(screen.getByRole("button", { name: /Cancel Request/i }));

    expect(mockOnRespond).toHaveBeenCalledWith("partnership-cancel", false);
  });

  it("renders relative time", () => {
    // Create a timestamp from 5 hours ago
    const fiveHoursAgo = new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString();
    const request = createMockRequest({ created_at: fiveHoursAgo });
    render(<PartnerRequestCard request={request} onRespond={mockOnRespond} />);

    // partners.hoursAgo = "{count}h ago"
    expect(screen.getByText("5h ago")).toBeInTheDocument();
  });

  it("renders 'just now' for recent requests", () => {
    const justNow = new Date().toISOString();
    const request = createMockRequest({ created_at: justNow });
    render(<PartnerRequestCard request={request} onRespond={mockOnRespond} />);

    // partners.justNow = "Just now"
    expect(screen.getByText("Just now")).toBeInTheDocument();
  });

  it("falls back to username when display_name is null", () => {
    const request = createMockRequest({
      display_name: null,
      username: "fallbackuser",
    });
    render(<PartnerRequestCard request={request} onRespond={mockOnRespond} />);

    // Display name should show the username
    expect(screen.getByText("fallbackuser")).toBeInTheDocument();
    // Avatar initial should be 'F' (from 'fallbackuser')
    expect(screen.getByText("F")).toBeInTheDocument();
  });
});
