import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CreatePrivateTableModal } from "../create-private-table-modal";
import type { PartnerInfo } from "@/stores";

// Mock the API client
vi.mock("@/lib/api/client", () => ({
  api: {
    post: vi.fn(),
  },
}));

const createMockPartner = (overrides?: Partial<PartnerInfo>): PartnerInfo => ({
  partnership_id: `partnership-${Math.random().toString(36).slice(2)}`,
  user_id: `user-${Math.random().toString(36).slice(2)}`,
  username: "studybuddy",
  display_name: "Study Buddy",
  avatar_config: {},
  pixel_avatar_id: null,
  study_interests: [],
  reliability_score: "85",
  last_session_together: null,
  ...overrides,
});

const mockPartners: PartnerInfo[] = [
  createMockPartner({ user_id: "user-1", display_name: "Alice", username: "alice" }),
  createMockPartner({ user_id: "user-2", display_name: "Bob", username: "bob" }),
  createMockPartner({ user_id: "user-3", display_name: "Charlie", username: "charlie" }),
];

describe("CreatePrivateTableModal", () => {
  const mockOnOpenChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders when open", () => {
    render(
      <CreatePrivateTableModal
        open={true}
        onOpenChange={mockOnOpenChange}
        partners={mockPartners}
      />
    );

    // Modal title should be visible
    expect(screen.getByText("Create Private Table")).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    render(
      <CreatePrivateTableModal
        open={false}
        onOpenChange={mockOnOpenChange}
        partners={mockPartners}
      />
    );

    // Modal content should not be in the document
    expect(screen.queryByText("Create Private Table")).not.toBeInTheDocument();
  });

  it("shows time slot selection on step 1", () => {
    render(
      <CreatePrivateTableModal
        open={true}
        onOpenChange={mockOnOpenChange}
        partners={mockPartners}
      />
    );

    // Step 1 instruction text
    expect(screen.getByText("Select Time Slot")).toBeInTheDocument();
    // Time slot buttons should be visible (6 slots)
    const timeButtons = screen.getAllByRole("button").filter((btn) => {
      // Time slot buttons contain Calendar icon and time text
      return btn.querySelector("svg") && btn.textContent?.match(/\d{1,2}:\d{2}/);
    });
    expect(timeButtons.length).toBe(6);
  });

  it("enables Next button after selecting time slot", async () => {
    render(
      <CreatePrivateTableModal
        open={true}
        onOpenChange={mockOnOpenChange}
        partners={mockPartners}
      />
    );

    // Next button should be disabled initially
    const nextButton = screen.getByRole("button", { name: /Next/i });
    expect(nextButton).toBeDisabled();

    // Click first time slot
    const timeSlots = screen.getAllByRole("button").filter((btn) => {
      return btn.querySelector("svg") && btn.textContent?.match(/\d{1,2}:\d{2}/);
    });
    await act(async () => {
      fireEvent.click(timeSlots[0]);
    });

    // Next button should now be enabled
    expect(nextButton).toBeEnabled();
  });

  it("advances to step 2 when Next clicked", async () => {
    render(
      <CreatePrivateTableModal
        open={true}
        onOpenChange={mockOnOpenChange}
        partners={mockPartners}
      />
    );

    // Select a time slot
    const timeSlots = screen.getAllByRole("button").filter((btn) => {
      return btn.querySelector("svg") && btn.textContent?.match(/\d{1,2}:\d{2}/);
    });
    await act(async () => {
      fireEvent.click(timeSlots[0]);
    });

    // Click Next
    const nextButton = screen.getByRole("button", { name: /Next/i });
    await act(async () => {
      fireEvent.click(nextButton);
    });

    // Step 2: Select partners - should show partner selection text
    expect(screen.getByText(/Select Partners to Invite/i)).toBeInTheDocument();
    // Partners should be listed
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("allows selecting partners", async () => {
    render(
      <CreatePrivateTableModal
        open={true}
        onOpenChange={mockOnOpenChange}
        partners={mockPartners}
      />
    );

    // Navigate to step 2
    const timeSlots = screen.getAllByRole("button").filter((btn) => {
      return btn.querySelector("svg") && btn.textContent?.match(/\d{1,2}:\d{2}/);
    });
    await act(async () => {
      fireEvent.click(timeSlots[0]);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    // Click on Alice to select
    const aliceButton = screen.getByRole("button", { name: /Alice/i });
    await act(async () => {
      fireEvent.click(aliceButton);
    });

    // Next button should now be enabled (partner selected)
    const nextButton = screen.getByRole("button", { name: /Next/i });
    expect(nextButton).toBeEnabled();
  });

  it("shows configuration options on step 3", async () => {
    render(
      <CreatePrivateTableModal
        open={true}
        onOpenChange={mockOnOpenChange}
        partners={mockPartners}
      />
    );

    // Navigate to step 3
    // Step 1: select time
    const timeSlots = screen.getAllByRole("button").filter((btn) => {
      return btn.querySelector("svg") && btn.textContent?.match(/\d{1,2}:\d{2}/);
    });
    await act(async () => {
      fireEvent.click(timeSlots[0]);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    // Step 2: select partner
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Alice/i }));
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    // Step 3: Configuration
    expect(screen.getByText("Table Mode")).toBeInTheDocument();
    expect(screen.getByText("Voice")).toBeInTheDocument();
    expect(screen.getByText("Quiet")).toBeInTheDocument();
    expect(screen.getByText("Max Seats")).toBeInTheDocument();
    expect(screen.getByText("Fill empty seats with AI")).toBeInTheDocument();
    expect(screen.getByText("Topic (optional)")).toBeInTheDocument();
  });

  it("shows summary on confirm step", async () => {
    render(
      <CreatePrivateTableModal
        open={true}
        onOpenChange={mockOnOpenChange}
        partners={mockPartners}
      />
    );

    // Navigate through all steps
    // Step 1: select time
    const timeSlots = screen.getAllByRole("button").filter((btn) => {
      return btn.querySelector("svg") && btn.textContent?.match(/\d{1,2}:\d{2}/);
    });
    await act(async () => {
      fireEvent.click(timeSlots[0]);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    // Step 2: select partner
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Alice/i }));
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    // Step 3: configure - click Next
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    // Step 4: confirm - should show review details
    expect(screen.getByText("Review Details")).toBeInTheDocument();
    expect(screen.getByText("Time")).toBeInTheDocument();
    expect(screen.getByText("Invitees")).toBeInTheDocument();
    expect(screen.getByText("Mode")).toBeInTheDocument();
    expect(screen.getByText("Seats")).toBeInTheDocument();
    // Create Table button should be visible
    expect(screen.getByRole("button", { name: /Create Table/i })).toBeInTheDocument();
  });

  it("goes back when Back clicked", async () => {
    render(
      <CreatePrivateTableModal
        open={true}
        onOpenChange={mockOnOpenChange}
        partners={mockPartners}
      />
    );

    // Navigate to step 2
    const timeSlots = screen.getAllByRole("button").filter((btn) => {
      return btn.querySelector("svg") && btn.textContent?.match(/\d{1,2}:\d{2}/);
    });
    await act(async () => {
      fireEvent.click(timeSlots[0]);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    // Verify we're on step 2
    expect(screen.getByText(/Select Partners to Invite/i)).toBeInTheDocument();

    // Click Back
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Back/i }));
    });

    // Should be back on step 1
    expect(screen.getByText("Select Time Slot")).toBeInTheDocument();
  });

  it("calls API on submit", async () => {
    const { api } = await import("@/lib/api/client");
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

    render(
      <CreatePrivateTableModal
        open={true}
        onOpenChange={mockOnOpenChange}
        partners={mockPartners}
      />
    );

    // Navigate through all steps
    // Step 1: select time
    const timeSlots = screen.getAllByRole("button").filter((btn) => {
      return btn.querySelector("svg") && btn.textContent?.match(/\d{1,2}:\d{2}/);
    });
    await act(async () => {
      fireEvent.click(timeSlots[0]);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    // Step 2: select partner (Alice with user_id "user-1")
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Alice/i }));
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    // Step 3: configure - click Next (use defaults)
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    // Step 4: Click Create Table
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Create Table/i }));
    });

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/api/v1/sessions/create-private", {
        time_slot: expect.any(String),
        partner_ids: ["user-1"],
        mode: "quiet",
        max_seats: 4,
        fill_ai: true,
        topic: null,
      });
    });
  });

  it("closes modal on successful submit", async () => {
    const { api } = await import("@/lib/api/client");
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

    render(
      <CreatePrivateTableModal
        open={true}
        onOpenChange={mockOnOpenChange}
        partners={mockPartners}
      />
    );

    // Navigate through all steps
    const timeSlots = screen.getAllByRole("button").filter((btn) => {
      return btn.querySelector("svg") && btn.textContent?.match(/\d{1,2}:\d{2}/);
    });
    await act(async () => {
      fireEvent.click(timeSlots[0]);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Alice/i }));
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Create Table/i }));
    });

    await waitFor(() => {
      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });
  });

  it("shows no partners message when partners list is empty", async () => {
    render(<CreatePrivateTableModal open={true} onOpenChange={mockOnOpenChange} partners={[]} />);

    // Navigate to step 2
    const timeSlots = screen.getAllByRole("button").filter((btn) => {
      return btn.querySelector("svg") && btn.textContent?.match(/\d{1,2}:\d{2}/);
    });
    await act(async () => {
      fireEvent.click(timeSlots[0]);
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Next/i }));
    });

    // Should show no partners message
    expect(screen.getByText("Add partners first to invite them")).toBeInTheDocument();
  });
});
