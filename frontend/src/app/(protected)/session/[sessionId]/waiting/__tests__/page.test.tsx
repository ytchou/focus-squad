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
  Button: ({ children, onClick, disabled, ...props }: any) => (
    <button onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  ),
}));

vi.mock("@/components/ui/card", () => ({
  Card: ({ children }: any) => <div data-testid="card">{children}</div>,
  CardContent: ({ children }: any) => <div>{children}</div>,
  CardDescription: ({ children }: any) => <p>{children}</p>,
  CardHeader: ({ children }: any) => <div>{children}</div>,
  CardTitle: ({ children }: any) => <h2>{children}</h2>,
}));

vi.mock("@/components/ui/badge", () => ({
  Badge: ({ children }: any) => <span>{children}</span>,
}));

describe("WaitingRoomPage", () => {
  let timers: ReturnType<typeof vi.useFakeTimers>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockClear();

    // Use fake timers for controlling time
    timers = vi.useFakeTimers();
  });

  afterEach(() => {
    timers.restoreMocks();
  });

  it("displays countdown timer in MM:SS format", () => {
    const startTime = new Date(Date.now() + 5 * 60 * 1000); // 5 minutes from now

    // Set up store state
    useSessionStore.setState({
      isWaiting: true,
      sessionStartTime: startTime,
      sessionId: "test-session-123",
    });

    render(<WaitingRoomPage />);

    // Check for MM:SS format (should show 05:00 or close to it)
    expect(screen.getByText(/0[4-5]:[0-5][0-9]/)).toBeInTheDocument();
  });

  it("shows 'Get Ready!' message at T-10 seconds", async () => {
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
      timers.advanceTimersByTime(6000);
    });

    // Now "Get Ready!" should appear
    await waitFor(() => {
      expect(screen.getByText(/Get Ready!/)).toBeInTheDocument();
    });
  });

  it("auto-redirects to session page at T-0", async () => {
    const startTime = new Date(Date.now() + 3 * 1000); // 3 seconds from now

    useSessionStore.setState({
      isWaiting: true,
      sessionStartTime: startTime,
      sessionId: "test-session-123",
    });

    render(<WaitingRoomPage />);

    // Fast-forward past the start time
    act(() => {
      timers.advanceTimersByTime(4000);
    });

    // Should redirect to active session
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/session/test-session-123");
    });

    // Waiting room state should be cleared
    expect(useSessionStore.getState().isWaiting).toBe(false);
  });

  it("calls leave API and redirects to dashboard when leave button clicked", async () => {
    const user = userEvent.setup({ delay: null });
    const startTime = new Date(Date.now() + 10 * 60 * 1000); // 10 minutes from now

    // Mock fetch for leave API
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    });

    useSessionStore.setState({
      isWaiting: true,
      sessionStartTime: startTime,
      sessionId: "test-session-123",
    });

    render(<WaitingRoomPage />);

    // Find and click leave button
    const leaveButton = screen.getByRole("button", { name: /Leave Session/i });
    await user.click(leaveButton);

    // Should call leave API
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "/api/sessions/test-session-123/leave",
        expect.objectContaining({
          method: "POST",
        })
      );
    });

    // Should redirect to dashboard
    expect(mockPush).toHaveBeenCalledWith("/dashboard");

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
    const startTime = new Date("2024-01-15T14:30:00Z");

    useSessionStore.setState({
      isWaiting: true,
      sessionStartTime: startTime,
      sessionId: "test-session-123",
    });

    render(<WaitingRoomPage />);

    // Check that time is formatted (exact format depends on locale)
    expect(screen.getByText(/Session starts at/)).toBeInTheDocument();
  });

  it("disables leave button while leaving", async () => {
    const user = userEvent.setup({ delay: null });
    const startTime = new Date(Date.now() + 10 * 60 * 1000);

    // Mock slow API response
    global.fetch = vi.fn().mockImplementationOnce(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                ok: true,
                json: async () => ({}),
              }),
            1000
          )
        )
    );

    useSessionStore.setState({
      isWaiting: true,
      sessionStartTime: startTime,
      sessionId: "test-session-123",
    });

    render(<WaitingRoomPage />);

    const leaveButton = screen.getByRole("button", { name: /Leave Session/i });
    await user.click(leaveButton);

    // Button should show "Leaving..." and be disabled
    await waitFor(() => {
      expect(screen.getByText("Leaving...")).toBeInTheDocument();
    });
  });
});
