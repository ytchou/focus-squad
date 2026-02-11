import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, act } from "@testing-library/react";
import SessionPage from "../page";
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
  Badge: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <span data-testid="badge" className={className}>
      {children}
    </span>
  ),
}));

vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({
    children,
    open,
  }: {
    children: React.ReactNode;
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
  }) => (open ? <div data-testid="dialog">{children}</div> : null),
  DialogContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dialog-content">{children}</div>
  ),
  DialogDescription: ({ children }: { children: React.ReactNode }) => <p>{children}</p>,
  DialogFooter: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: Object.assign(vi.fn(), { info: vi.fn() }),
}));

// Mock board store
vi.mock("@/stores/board-store", () => ({
  useBoardStore: Object.assign(
    () => ({
      messages: [],
      addMessage: vi.fn(),
      saveReflection: vi.fn(),
      loadSessionReflections: vi.fn(),
      reset: vi.fn(),
      isDrawerOpen: false,
      toggleDrawer: vi.fn(),
      unreadCount: 0,
    }),
    { getState: () => ({ reset: vi.fn() }) }
  ),
}));

// Mock pixel session layout
vi.mock("@/components/session/pixel", () => ({
  PixelSessionLayout: ({ sessionId }: { sessionId: string }) => (
    <div data-testid="pixel-session-layout">Pixel Layout: {sessionId}</div>
  ),
}));

// Mock session components
vi.mock("@/components/session", () => ({
  SessionLayout: ({
    header,
    children,
    controls,
  }: {
    header: React.ReactNode;
    children: React.ReactNode;
    controls: React.ReactNode;
  }) => (
    <div data-testid="session-layout">
      <div data-testid="session-header">{header}</div>
      <div data-testid="session-content">{children}</div>
      <div data-testid="session-controls">{controls}</div>
    </div>
  ),
  SessionHeader: ({
    phase,
    onLeave,
  }: {
    sessionId: string;
    phase: string;
    onLeave?: () => Promise<void>;
  }) => (
    <div data-testid="session-header-component">
      <span data-testid="phase-label">{phase}</span>
      <button onClick={onLeave} data-testid="leave-button">
        Leave
      </button>
    </div>
  ),
  TimerDisplay: ({
    phase,
    timeRemaining,
  }: {
    phase: string;
    timeRemaining: number;
    totalTimeRemaining: number;
    progress: number;
  }) => (
    <div data-testid="timer-display">
      <span data-testid="timer-phase">{phase}</span>
      <span data-testid="timer-remaining">{timeRemaining}</span>
    </div>
  ),
  TableView: ({
    participants,
  }: {
    participants: Array<{ id: string; username: string | null; displayName: string | null }>;
    speakingParticipantIds: Set<string>;
    currentUserId: string | null;
  }) => (
    <div data-testid="table-view">
      {participants.map((p) => (
        <div key={p.id} data-testid={`participant-${p.id}`}>
          {p.displayName || p.username || "Unknown"}
        </div>
      ))}
    </div>
  ),
  ControlBar: ({
    isMuted,
    isQuietMode,
  }: {
    isMuted: boolean;
    isQuietMode: boolean;
    onToggleMute: () => void;
  }) => (
    <div data-testid="control-bar">
      <span data-testid="muted-state">{isMuted ? "muted" : "unmuted"}</span>
      <span data-testid="quiet-mode">{isQuietMode ? "quiet" : "normal"}</span>
    </div>
  ),
  CompactTableView: () => <div data-testid="compact-table-view" />,
  SessionBoard: () => <div data-testid="session-board" />,
  BoardDrawer: () => <div data-testid="board-drawer" />,
}));

// Mock LiveKit provider
vi.mock("@/components/session/livekit-room-provider", () => ({
  LiveKitRoomProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="livekit-provider">{children}</div>
  ),
  useActiveSpeakers: () => new Set<string>(),
  useLocalMicrophone: () => ({ isMuted: true, toggleMute: vi.fn() }),
  useDataChannel: () => ({ sendMessage: vi.fn() }),
}));

// Mock SessionEndModal
vi.mock("@/components/session/session-end-modal", () => ({
  SessionEndModal: ({
    open,
    phase,
  }: {
    open: boolean;
    onClose: () => void;
    sessionId: string;
    phase: string;
  }) =>
    open ? (
      <div data-testid="session-end-modal">
        <span data-testid="end-modal-phase">{phase}</span>
      </div>
    ) : null,
}));

// Mock lucide-react
vi.mock("lucide-react", () => ({
  Loader2: ({ className }: { className?: string }) => (
    <span data-testid="loader" className={className}>
      Loading...
    </span>
  ),
  Bug: () => <span>Bug</span>,
  LogOut: () => <span>LogOut</span>,
  Mic: () => <span>Mic</span>,
  MicOff: () => <span>MicOff</span>,
  Activity: () => <span>Activity</span>,
  CheckCircle: () => <span>CheckCircle</span>,
  Star: () => <span>Star</span>,
  Clock: () => <span>Clock</span>,
  Target: () => <span>Target</span>,
  Coffee: () => <span>Coffee</span>,
  MessageCircle: () => <span>MessageCircle</span>,
  MessageSquare: () => <span>MessageSquare</span>,
  ChevronRight: () => <span>ChevronRight</span>,
  ChevronLeft: () => <span>ChevronLeft</span>,
  ChevronUp: () => <span>ChevronUp</span>,
  ChevronDown: () => <span>ChevronDown</span>,
  Send: () => <span>Send</span>,
  ThumbsUp: () => <span>ThumbsUp</span>,
  ThumbsDown: () => <span>ThumbsDown</span>,
  Minus: () => <span>Minus</span>,
  Bot: () => <span>Bot</span>,
  Wifi: () => <span>Wifi</span>,
  WifiOff: () => <span>WifiOff</span>,
  Volume2: () => <span>Volume2</span>,
  VolumeX: () => <span>VolumeX</span>,
  Check: () => <span>Check</span>,
}));

// Mock api client
const mockApiGet = vi.fn();
const mockApiPost = vi.fn().mockResolvedValue({});

vi.mock("@/lib/api/client", () => ({
  api: {
    get: (...args: unknown[]) => mockApiGet(...args),
    post: (...args: unknown[]) => mockApiPost(...args),
  },
}));

// Mock hooks
vi.mock("@/hooks/use-session-timer", () => ({
  useSessionTimer: ({ sessionStartTime }: { sessionStartTime: Date | string | null }) => {
    if (!sessionStartTime) {
      return {
        phase: "idle",
        timeRemaining: 0,
        totalTimeRemaining: 0,
        progress: 0,
        elapsedMinutes: 0,
        isRunning: false,
      };
    }
    // Default: return work1 phase for tests
    return {
      phase: "work1",
      timeRemaining: 1200,
      totalTimeRemaining: 2400,
      progress: 0.2,
      elapsedMinutes: 8,
      isRunning: true,
    };
  },
}));

vi.mock("@/hooks/use-activity-tracking", () => ({
  useActivityTracking: () => ({
    isActive: false,
    lastActivityAt: null,
  }),
}));

vi.mock("@/hooks/use-presence-detection", () => ({
  usePresenceDetection: () => ({
    presenceState: "active",
    isTyping: false,
  }),
}));

vi.mock("@/hooks/use-picture-in-picture", () => ({
  usePictureInPicture: () => ({
    isPiPActive: false,
    isPiPSupported: false,
    togglePiP: vi.fn(),
  }),
}));

vi.mock("@/components/session/activity-consent-prompt", () => ({
  ActivityConsentPrompt: () => null,
  getStoredConsent: () => "granted",
}));

// Helper session API response — 4 participants to prevent polling interval
const mockSessionResponse = {
  id: "test-session-123",
  start_time: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
  end_time: new Date(Date.now() + 47 * 60 * 1000).toISOString(),
  mode: "forced_audio",
  topic: null,
  language: "en",
  current_phase: "work1",
  phase_started_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
  participants: [
    {
      id: "p1",
      user_id: "user-1",
      participant_type: "human",
      seat_number: 1,
      username: "alice",
      display_name: "Alice",
      avatar_config: {},
      pixel_avatar_id: null,
      joined_at: new Date().toISOString(),
      is_active: true,
      ai_companion_name: null,
    },
    {
      id: "p2",
      user_id: "user-2",
      participant_type: "human",
      seat_number: 2,
      username: "bob",
      display_name: "Bob",
      avatar_config: {},
      pixel_avatar_id: null,
      joined_at: new Date().toISOString(),
      is_active: true,
      ai_companion_name: null,
    },
    {
      id: "p3",
      user_id: "ai-1",
      participant_type: "ai_companion",
      seat_number: 3,
      username: null,
      display_name: null,
      avatar_config: {},
      pixel_avatar_id: null,
      joined_at: new Date().toISOString(),
      is_active: true,
      ai_companion_name: "Study Buddy",
    },
    {
      id: "p4",
      user_id: "ai-2",
      participant_type: "ai_companion",
      seat_number: 4,
      username: null,
      display_name: null,
      avatar_config: {},
      pixel_avatar_id: null,
      joined_at: new Date().toISOString(),
      is_active: true,
      ai_companion_name: "Focus Friend",
    },
  ],
  room_type: "cozy-study",
  available_seats: 2,
  livekit_room_name: "room-123",
};

const mockUserProfile = {
  id: "user-1",
  credit_tier: "free",
};

// Setup mock that resolves both API calls for a successful session render
function setupSuccessfulApiMocks() {
  mockApiGet.mockImplementation((path: string) => {
    if (path.includes("/sessions/")) return Promise.resolve(mockSessionResponse);
    if (path.includes("/users/me")) return Promise.resolve(mockUserProfile);
    return Promise.resolve({});
  });
}

// Render SessionPage and flush all async work (API calls, state updates, effects)
// by wrapping in act(). Since API mocks resolve via microtasks, this flushes everything.
async function renderAndSettle() {
  await act(async () => {
    render(<SessionPage />);
  });
}

describe("SessionPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiGet.mockReset();
    mockApiPost.mockReset();
    mockApiPost.mockResolvedValue({});

    // Default to classic view mode for existing tests
    localStorage.setItem("sessionViewMode", "classic");

    // Set up session store with start time (no LiveKit token by default)
    useSessionStore.setState({
      sessionId: "test-session-123",
      sessionStartTime: new Date(Date.now() - 8 * 60 * 1000),
      livekitToken: null,
      livekitServerUrl: null,
      isQuietMode: false,
      showEndModal: false,
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("shows loading state initially", async () => {
    // API call stays pending so component stays in loading state.
    // Use a promise we can settle to avoid leaked async work.
    let resolvePending: (value: unknown) => void;
    mockApiGet.mockReturnValue(
      new Promise((resolve) => {
        resolvePending = resolve;
      })
    );

    render(<SessionPage />);

    expect(screen.getByText("Loading session...")).toBeInTheDocument();
    expect(screen.getByTestId("loader")).toBeInTheDocument();

    // Settle the pending promise before cleanup to prevent leaked work.
    await act(async () => {
      resolvePending(mockSessionResponse);
    });
  });

  it("renders session layout with timer and participants after loading", async () => {
    setupSuccessfulApiMocks();
    await renderAndSettle();

    expect(screen.getByTestId("session-layout")).toBeInTheDocument();
    expect(screen.getByTestId("timer-display")).toBeInTheDocument();
    expect(screen.getByTestId("table-view")).toBeInTheDocument();
    expect(screen.getByTestId("control-bar")).toBeInTheDocument();
  });

  it("shows end modal when showEndModal state is true", async () => {
    setupSuccessfulApiMocks();
    useSessionStore.setState({ showEndModal: true });
    await renderAndSettle();

    expect(screen.getByTestId("session-end-modal")).toBeInTheDocument();
  });

  it("does not show end modal when showEndModal state is false", async () => {
    setupSuccessfulApiMocks();
    useSessionStore.setState({ showEndModal: false });
    await renderAndSettle();

    expect(screen.getByTestId("session-layout")).toBeInTheDocument();
    expect(screen.queryByTestId("session-end-modal")).not.toBeInTheDocument();
  });

  it("leave button exists and is clickable", async () => {
    setupSuccessfulApiMocks();
    await renderAndSettle();

    const leaveButton = screen.getByTestId("leave-button");
    expect(leaveButton).toBeInTheDocument();
    expect(leaveButton).not.toBeDisabled();
  });

  it("calls leaveSession and API on leave", async () => {
    setupSuccessfulApiMocks();
    await renderAndSettle();

    await act(async () => {
      screen.getByTestId("leave-button").click();
    });

    expect(mockApiPost).toHaveBeenCalledWith("/sessions/test-session-123/leave");
  });

  it("renders timer display with phase info", async () => {
    setupSuccessfulApiMocks();
    await renderAndSettle();

    expect(screen.getByTestId("timer-display")).toBeInTheDocument();
    expect(screen.getByTestId("timer-phase")).toHaveTextContent("work1");
    expect(screen.getByTestId("timer-remaining")).toHaveTextContent("1200");
  });

  it("shows error state when API fails", async () => {
    mockApiGet.mockRejectedValue(new Error("Network error"));
    await renderAndSettle();

    expect(screen.getByText("Failed to load session. Please try again.")).toBeInTheDocument();
  });

  it("shows 'Return to Dashboard' link on error", async () => {
    mockApiGet.mockRejectedValue(new Error("Network error"));
    await renderAndSettle();

    expect(screen.getByText("Return to Dashboard")).toBeInTheDocument();

    await act(async () => {
      screen.getByText("Return to Dashboard").click();
    });
    expect(mockPush).toHaveBeenCalledWith("/dashboard");
  });

  it("displays participant usernames", async () => {
    setupSuccessfulApiMocks();
    await renderAndSettle();

    expect(screen.getByTestId("table-view")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
  });

  it("renders phase label in session header", async () => {
    setupSuccessfulApiMocks();
    await renderAndSettle();

    expect(screen.getByTestId("phase-label")).toBeInTheDocument();
    expect(screen.getByTestId("phase-label")).toHaveTextContent("work1");
  });
});
