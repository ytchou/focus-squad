import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ReportModal } from "../report-modal";

// Mock the API client
vi.mock("@/lib/api/client", () => ({
  api: {
    post: vi.fn(),
  },
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  reportedUserId: "user-123",
  reportedDisplayName: "Test User",
  sessionId: "session-456",
};

describe("ReportModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all 5 report categories", () => {
    render(<ReportModal {...defaultProps} />);

    expect(screen.getByText("Verbal Harassment")).toBeInTheDocument();
    expect(screen.getByText("Explicit Content")).toBeInTheDocument();
    expect(screen.getByText("Threatening Behavior")).toBeInTheDocument();
    expect(screen.getByText("Spam / Scam")).toBeInTheDocument();
    expect(screen.getByText("Other")).toBeInTheDocument();
  });

  it("displays reported user name in title", () => {
    render(<ReportModal {...defaultProps} />);
    expect(screen.getByText("Report Test User")).toBeInTheDocument();
  });

  it("disables submit button until category is selected", () => {
    render(<ReportModal {...defaultProps} />);
    const submitButton = screen.getByRole("button", { name: /submit report/i });
    expect(submitButton).toBeDisabled();
  });

  it("enables submit button when category is selected", () => {
    render(<ReportModal {...defaultProps} />);

    fireEvent.click(screen.getByText("Verbal Harassment"));
    const submitButton = screen.getByRole("button", { name: /submit report/i });
    expect(submitButton).toBeEnabled();
  });

  it("calls API with correct payload on submit", async () => {
    const { api } = await import("@/lib/api/client");
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

    render(<ReportModal {...defaultProps} />);

    fireEvent.click(screen.getByText("Threatening Behavior"));
    fireEvent.click(screen.getByRole("button", { name: /submit report/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/moderation/reports", {
        reported_user_id: "user-123",
        session_id: "session-456",
        category: "threatening_behavior",
        description: undefined,
      });
    });
  });

  it("shows success toast and closes on successful submission", async () => {
    const { api } = await import("@/lib/api/client");
    const { toast } = await import("sonner");
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

    render(<ReportModal {...defaultProps} />);

    fireEvent.click(screen.getByText("Spam / Scam"));
    fireEvent.click(screen.getByRole("button", { name: /submit report/i }));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith("Report submitted. Our team will review it.");
      expect(defaultProps.onClose).toHaveBeenCalled();
    });
  });

  it("shows error toast on API failure", async () => {
    const { api } = await import("@/lib/api/client");
    const { toast } = await import("sonner");
    (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error("fail"));

    render(<ReportModal {...defaultProps} />);

    fireEvent.click(screen.getByText("Other"));
    fireEvent.click(screen.getByRole("button", { name: /submit report/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Failed to submit report. Please try again.");
    });
  });

  it("includes description in payload when provided", async () => {
    const { api } = await import("@/lib/api/client");
    (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

    render(<ReportModal {...defaultProps} />);

    fireEvent.click(screen.getByText("Verbal Harassment"));
    const textarea = screen.getByPlaceholderText("Provide any additional context...");
    fireEvent.change(textarea, { target: { value: "They were being rude" } });
    fireEvent.click(screen.getByRole("button", { name: /submit report/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/moderation/reports", {
        reported_user_id: "user-123",
        session_id: "session-456",
        category: "verbal_harassment",
        description: "They were being rude",
      });
    });
  });

  it("shows character count for description", () => {
    render(<ReportModal {...defaultProps} />);
    expect(screen.getByText("0/2000")).toBeInTheDocument();
  });
});
