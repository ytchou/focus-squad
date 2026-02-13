import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { PartnerCard } from "../partner-card";
import type { PartnerInfo } from "@/stores";

const createMockPartner = (overrides?: Partial<PartnerInfo>): PartnerInfo => ({
  partnership_id: "partnership-123",
  user_id: "user-456",
  username: "studybuddy",
  display_name: "Study Buddy",
  avatar_config: {},
  pixel_avatar_id: null,
  study_interests: ["coding", "reading"],
  reliability_score: "85",
  last_session_together: null,
  ...overrides,
});

describe("PartnerCard", () => {
  const mockOnRemove = vi.fn();
  const mockOnMessage = vi.fn();
  const mockOnVisitRoom = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders partner display name", () => {
    const partner = createMockPartner({ display_name: "Focus Friend" });
    render(<PartnerCard partner={partner} onRemove={mockOnRemove} />);

    expect(screen.getByText("Focus Friend")).toBeInTheDocument();
  });

  it("renders partner username with @ prefix", () => {
    const partner = createMockPartner({ username: "focusfriend" });
    render(<PartnerCard partner={partner} onRemove={mockOnRemove} />);

    expect(screen.getByText("@focusfriend")).toBeInTheDocument();
  });

  it("renders interest tags", () => {
    const partner = createMockPartner({
      study_interests: ["coding", "writing", "design"],
    });
    render(<PartnerCard partner={partner} onRemove={mockOnRemove} />);

    // Tags are translated via partners.tags.{tag}
    // The mock returns fallback key format for nested keys
    expect(screen.getByText("partners.tags.coding")).toBeInTheDocument();
    expect(screen.getByText("partners.tags.writing")).toBeInTheDocument();
    expect(screen.getByText("partners.tags.design")).toBeInTheDocument();
  });

  it("renders avatar initial", () => {
    const partner = createMockPartner({ display_name: "Jane Doe" });
    render(<PartnerCard partner={partner} onRemove={mockOnRemove} />);

    // Initial is first character of display name, uppercased
    expect(screen.getByText("J")).toBeInTheDocument();
  });

  it("renders remove button", () => {
    const partner = createMockPartner();
    render(<PartnerCard partner={partner} onRemove={mockOnRemove} />);

    // partners.remove = "Remove"
    expect(screen.getByRole("button", { name: /Remove/i })).toBeInTheDocument();
  });

  it("shows confirmation on remove click", () => {
    const partner = createMockPartner();
    render(<PartnerCard partner={partner} onRemove={mockOnRemove} />);

    // Click remove button
    const removeButton = screen.getByRole("button", { name: /Remove/i });
    fireEvent.click(removeButton);

    // Confirm and cancel buttons should appear
    // partners.confirmRemove = "Confirm Remove"
    // common.cancel = "Cancel" (generic cancel button)
    expect(screen.getByRole("button", { name: /Confirm Remove/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Cancel$/i })).toBeInTheDocument();
  });

  it("calls onRemove when confirmed", () => {
    const partner = createMockPartner({ partnership_id: "partnership-abc" });
    render(<PartnerCard partner={partner} onRemove={mockOnRemove} />);

    // Click remove, then confirm
    fireEvent.click(screen.getByRole("button", { name: /Remove/i }));
    fireEvent.click(screen.getByRole("button", { name: /Confirm Remove/i }));

    expect(mockOnRemove).toHaveBeenCalledWith("partnership-abc");
  });

  it("cancels removal", () => {
    const partner = createMockPartner();
    render(<PartnerCard partner={partner} onRemove={mockOnRemove} />);

    // Click remove, then cancel
    fireEvent.click(screen.getByRole("button", { name: /Remove/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Cancel$/i }));

    // Should go back to showing the remove button
    expect(screen.getByRole("button", { name: /Remove/i })).toBeInTheDocument();
    expect(mockOnRemove).not.toHaveBeenCalled();
  });

  it("renders message button when onMessage provided", () => {
    const partner = createMockPartner();
    render(<PartnerCard partner={partner} onRemove={mockOnRemove} onMessage={mockOnMessage} />);

    // partners.tabs.messages = "Messages"
    expect(screen.getByRole("button", { name: /Messages/i })).toBeInTheDocument();
  });

  it("calls onMessage when clicked", () => {
    const partner = createMockPartner({ user_id: "user-xyz" });
    render(<PartnerCard partner={partner} onRemove={mockOnRemove} onMessage={mockOnMessage} />);

    fireEvent.click(screen.getByRole("button", { name: /Messages/i }));

    expect(mockOnMessage).toHaveBeenCalledWith("user-xyz");
  });

  it("renders visit room button when onVisitRoom provided", () => {
    const partner = createMockPartner();
    render(<PartnerCard partner={partner} onRemove={mockOnRemove} onVisitRoom={mockOnVisitRoom} />);

    // partners.visitRoom = "Visit Room"
    expect(screen.getByRole("button", { name: /Visit Room/i })).toBeInTheDocument();
  });

  it("falls back to username when display_name is null", () => {
    const partner = createMockPartner({
      display_name: null,
      username: "fallbackuser",
    });
    render(<PartnerCard partner={partner} onRemove={mockOnRemove} />);

    // The display name should show the username
    // Avatar initial should be 'F' (from 'fallbackuser')
    expect(screen.getByText("fallbackuser")).toBeInTheDocument();
    expect(screen.getByText("F")).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Relative time display tests
  // -------------------------------------------------------------------------
  describe("relative time display", () => {
    it("displays 'today' when last session was today", () => {
      // Create a date that's earlier today (a few hours ago)
      const today = new Date();
      today.setHours(today.getHours() - 2);
      const partner = createMockPartner({
        last_session_together: today.toISOString(),
      });
      render(<PartnerCard partner={partner} onRemove={mockOnRemove} />);

      // partners.today = "Today" (from en.json)
      expect(screen.getByText("Today")).toBeInTheDocument();
    });

    it("displays 'yesterday' when last session was yesterday", () => {
      // Create a date that's exactly 1 day ago
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      const partner = createMockPartner({
        last_session_together: yesterday.toISOString(),
      });
      render(<PartnerCard partner={partner} onRemove={mockOnRemove} />);

      // partners.yesterday = "Yesterday"
      expect(screen.getByText("Yesterday")).toBeInTheDocument();
    });

    it("displays 'X days ago' for sessions more than 1 day ago", () => {
      // Create a date that's 5 days ago
      const fiveDaysAgo = new Date();
      fiveDaysAgo.setDate(fiveDaysAgo.getDate() - 5);
      const partner = createMockPartner({
        last_session_together: fiveDaysAgo.toISOString(),
      });
      render(<PartnerCard partner={partner} onRemove={mockOnRemove} />);

      // partners.daysAgo = "{count} days ago" - mock returns key with params
      // The mock translator will return "partners.daysAgo" for nested keys
      expect(screen.getByText(/days ago/i)).toBeInTheDocument();
    });

    it("displays 'never studied' when no last session", () => {
      const partner = createMockPartner({
        last_session_together: null,
      });
      render(<PartnerCard partner={partner} onRemove={mockOnRemove} />);

      // partners.neverStudied = "Haven't studied together yet"
      expect(screen.getByText(/studied together yet/i)).toBeInTheDocument();
    });
  });
});
