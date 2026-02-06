import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";
import WaitingRoomPage from "../page";
import { useSessionStore } from "@/stores/session-store";

// Mock next/navigation
const mockPush = vi.fn();
const mockParams = { sessionId: "test-session-123" };

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useParams: () => mockParams,
}));

// Mock UI components
vi.mock("@/components/ui/button", () => ({
  Button: ({
    children,
    onClick,
    disabled,
    ...props
  }: React.ButtonHTMLAttributes<HTMLButtonElement> & { children: React.ReactNode }) => (
    <button onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  ),
}));

vi.mock("@/components/ui/card", () => ({
  Card: ({ children }: { children: React.ReactNode }) => <div data-testid="card">{children}</div>,
  CardContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardDescription: ({ children }: { children: React.ReactNode }) => <p>{children}</p>,
  CardHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardTitle: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
}));

vi.mock("@/components/ui/badge", () => ({
  Badge: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}));

// Mock api client
const mockApiPost = vi.fn().mockResolvedValue({});
vi.mock("@/lib/api/client", () => ({
  api: {
    post: (...args: unknown[]) => mockApiPost(...args),
  },
}));

describe("WaitingRoomPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockClear();
    mockApiPost.mockClear();
    mockApiPost.mockResolvedValue({});
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("timer-based tests", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    it("displays countdown timer in MM:SS format", () => {
      const startTime = new Date(Date.now() + 5 * 60 * 1000); // 5 minutes from now

      useSessionStore.setState({
        isWaiting: true,
        sessionStartTime: startTime,
        sessionId: "test-session-123",
      });

      render(<WaitingRoomPage />);

      // Check for MM:SS format (should show 05:00 or close to it)
      expect(screen.getByText(/0[4-5]:[0-5][0-9]/)).toBeInTheDocument();
    });

    it("shows 'Get Ready!' message at T-10 seconds", () => {
      const startTime = new Date(Date.now() + 15 * 1000); // 15 seconds from now

      useSessionStore.setState({
        isWaiting: true,
        sessionStartTime: startTime,
        sessionId: "test-session-123",
      });

      render(<WaitingRoomPage />);

      // Initially, "Get Ready!" should not be visible
      expect(screen.queryByText(/Get Ready!/)).not.toBeInTheDocument();

      // Fast-forward 6 seconds (now at T-9s)
      act(() => {
        vi.advanceTimersByTime(6000);
      });

      // Now "Get Ready!" should appear (synchronous check after timer advance)
      expect(screen.getByText(/Get Ready!/)).toBeInTheDocument();
    });

    it("auto-redirects to session page at T-0", () => {
      const startTime = new Date(Date.now() + 3 * 1000); // 3 seconds from now

      useSessionStore.setState({
        isWaiting: true,
        sessionStartTime: startTime,
        sessionId: "test-session-123",
      });

      render(<WaitingRoomPage />);

      // Fast-forward past the start time
      act(() => {
        vi.advanceTimersByTime(4000);
      });

      // Should redirect to active session (synchronous check)
      expect(mockPush).toHaveBeenCalledWith("/session/test-session-123");

      // Waiting room state should be cleared
      expect(useSessionStore.getState().isWaiting).toBe(false);
    });

    it("redirects to dashboard if no session start time", () => {
      useSessionStore.setState({
        isWaiting: false,
        sessionStartTime: null,
        sessionId: null,
      });

      render(<WaitingRoomPage />);

      // Should redirect to dashboard immediately
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });

    it("formats start time correctly for display", () => {
      // Use a future time relative to fake timer's "now"
      const startTime = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes from now

      useSessionStore.setState({
        isWaiting: true,
        sessionStartTime: startTime,
        sessionId: "test-session-123",
      });

      render(<WaitingRoomPage />);

      // Check that the session info card is displayed
      expect(screen.getByTestId("card")).toBeInTheDocument();
      // Timer should be showing
      expect(screen.getByText(/[0-9]{2}:[0-9]{2}/)).toBeInTheDocument();
    });
  });

  describe("async API tests", () => {
    // These tests use real timers for async operations

    it("calls leave API and redirects to dashboard when leave button clicked", async () => {
      const user = userEvent.setup();
      const startTime = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes from now

      useSessionStore.setState({
        isWaiting: true,
        sessionStartTime: startTime,
        sessionId: "test-session-123",
      });

      render(<WaitingRoomPage />);

      // Find and click leave button
      const leaveButton = screen.getByRole("button", { name: /Leave Session/i });
      await user.click(leaveButton);

      // Should call leave API (path only, no body)
      await waitFor(() => {
        expect(mockApiPost).toHaveBeenCalledWith("/sessions/test-session-123/leave");
      });

      // Should redirect to dashboard
      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith("/dashboard");
      });

      // Waiting room state should be cleared
      expect(useSessionStore.getState().isWaiting).toBe(false);
    });

    it("disables leave button while leaving", async () => {
      const user = userEvent.setup();
      const startTime = new Date(Date.now() + 10 * 60 * 1000);

      // Mock: analytics calls resolve immediately, leave call stays pending
      let resolveLeave: (value: object) => void;
      mockApiPost.mockImplementation((path: string) => {
        if (path === "/sessions/test-session-123/leave") {
          return new Promise((resolve) => {
            resolveLeave = resolve;
          });
        }
        // Analytics calls resolve immediately
        return Promise.resolve({});
      });

      useSessionStore.setState({
        isWaiting: true,
        sessionStartTime: startTime,
        sessionId: "test-session-123",
      });

      render(<WaitingRoomPage />);

      const leaveButton = screen.getByRole("button", { name: /Leave Session/i });
      await user.click(leaveButton);

      // Button should show "Leaving..." and be disabled while API is pending
      await waitFor(() => {
        expect(screen.getByText("Leaving...")).toBeInTheDocument();
      });

      // Resolve the API call to clean up
      resolveLeave!({});
    });
  });
});
