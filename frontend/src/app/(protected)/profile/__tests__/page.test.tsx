import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// ─── Mock Data ──────────────────────────────────────────────────────────────

const mockUser = {
  id: "user-uuid-123",
  auth_id: "auth-abc-123",
  email: "test@example.com",
  username: "testuser",
  display_name: "Test User",
  bio: "I love studying",
  avatar_config: {},
  pixel_avatar_id: "char-1",
  is_onboarded: true,
  default_table_mode: "forced_audio" as const,
  reliability_score: 92,
  total_focus_minutes: 1200,
  session_count: 24,
  current_streak: 5,
  longest_streak: 12,
  last_session_date: "2025-02-01",
  language: "en",
  activity_tracking_enabled: false,
  email_notifications_enabled: true,
  push_notifications_enabled: true,
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
  banned_until: null,
  deleted_at: null,
  credits_remaining: 2,
  credits_used_this_week: 0,
  credit_tier: "free" as const,
  credit_refresh_date: null,
};

// ─── Mocks ──────────────────────────────────────────────────────────────────

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

const mockApiPatch = vi.fn();
const mockApiDelete = vi.fn();

vi.mock("@/lib/api/client", () => ({
  api: {
    patch: (...args: unknown[]) => mockApiPatch(...args),
    delete: (...args: unknown[]) => mockApiDelete(...args),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

const mockSignOut = vi.fn().mockResolvedValue({});

vi.mock("@/lib/supabase/client", () => ({
  createClient: () => ({
    auth: { signOut: mockSignOut },
  }),
}));

// Mock user store - supports both hook usage and getState
let currentUser: typeof mockUser | null = mockUser;
const mockSetUser = vi.fn();
const mockClearUser = vi.fn();

vi.mock("@/stores/user-store", () => {
  const hook = (selector?: (state: Record<string, unknown>) => unknown) => {
    const state = { user: currentUser };
    return selector ? selector(state) : state;
  };
  return {
    useUserStore: Object.assign(hook, {
      getState: () => ({
        user: currentUser,
        setUser: mockSetUser,
        clearUser: mockClearUser,
      }),
    }),
    type: {} as never,
  };
});

// Mock CharacterPicker
vi.mock("@/components/character-picker", () => ({
  CharacterPicker: ({
    onSelect,
  }: {
    onSelect: (id: string) => void;
    selectedId?: string | null;
  }) => (
    <div data-testid="character-picker">
      <button data-testid="pick-char-3" onClick={() => onSelect("char-3")}>
        Pick char-3
      </button>
    </div>
  ),
}));

vi.mock("@/config/pixel-rooms", () => ({
  PIXEL_CHARACTERS: {
    "char-1": {
      id: "char-1",
      name: "Scholar",
      spriteSheet: "/test.png",
      frameWidth: 64,
      frameHeight: 64,
      states: {
        working: { frames: 4, fps: 4, row: 0 },
        speaking: { frames: 4, fps: 6, row: 1 },
        away: { frames: 3, fps: 3, row: 2 },
      },
    },
  },
  CHARACTER_IDS: ["char-1"],
  DEFAULT_CHARACTER: "char-1",
}));

// Mock layout and UI components to simplify rendering
vi.mock("@/components/layout", () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="app-shell">{children}</div>
  ),
}));

vi.mock("@/components/ui/stat-card", () => ({
  StatCard: ({
    title,
    value,
    subtitle,
  }: {
    title: string;
    value: number;
    icon: unknown;
    subtitle?: string;
  }) => (
    <div data-testid={`stat-${title.toLowerCase().replace(/\s/g, "-")}`}>
      <span>{title}</span>
      <span data-testid="stat-value">{value}</span>
      {subtitle && <span>{subtitle}</span>}
    </div>
  ),
}));

vi.mock("@/components/ui/reliability-badge", () => ({
  ReliabilityBadge: ({ score }: { score: number; size?: string }) => (
    <span data-testid="reliability-badge">{score}</span>
  ),
}));

// Dialog mock - renders children when open
vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({
    open,
    children,
  }: {
    open: boolean;
    onOpenChange: (v: boolean) => void;
    children: React.ReactNode;
  }) => (open ? <div data-testid="dialog">{children}</div> : null),
  DialogContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <h2>{children}</h2>,
}));

vi.mock("@/components/ui/button", () => ({
  Button: ({
    children,
    onClick,
    disabled,
    variant,
    ...props
  }: React.ButtonHTMLAttributes<HTMLButtonElement> & {
    children: React.ReactNode;
    variant?: string;
  }) => (
    <button onClick={onClick} disabled={disabled} data-variant={variant} {...props}>
      {children}
    </button>
  ),
}));

vi.mock("@/lib/utils", () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(" "),
}));

import ProfilePage from "../page";

// ─── Tests ──────────────────────────────────────────────────────────────────

describe("ProfilePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentUser = { ...mockUser };
  });

  // ── Loading state ───────────────────────────────────────────────────────

  it("shows loading state when user is null", () => {
    currentUser = null;
    render(<ProfilePage />);

    expect(screen.getByText("Loading profile...")).toBeInTheDocument();
  });

  // ── Identity Section ────────────────────────────────────────────────────

  describe("Identity Section", () => {
    it("renders display name and username", () => {
      render(<ProfilePage />);

      expect(screen.getByText("Test User")).toBeInTheDocument();
      expect(screen.getByText("@testuser")).toBeInTheDocument();
    });

    it("renders bio", () => {
      render(<ProfilePage />);

      expect(screen.getByText("I love studying")).toBeInTheDocument();
    });

    it("enters edit mode and shows form fields", () => {
      render(<ProfilePage />);

      // Click the edit (pencil) button
      const editButtons = screen.getAllByRole("button");
      const pencilButton = editButtons.find(
        (btn) => btn.querySelector("svg") && btn.closest("section")
      );
      if (pencilButton) {
        fireEvent.click(pencilButton);
        // Should now show input fields
        expect(screen.getByDisplayValue("testuser")).toBeInTheDocument();
        expect(screen.getByDisplayValue("Test User")).toBeInTheDocument();
      }
    });

    it("saves profile changes via API", async () => {
      const updatedProfile = { ...mockUser, username: "newname" };
      mockApiPatch.mockResolvedValueOnce(updatedProfile);

      render(<ProfilePage />);

      // Enter edit mode
      const editButtons = screen.getAllByRole("button");
      const pencilButton = editButtons.find(
        (btn) => btn.querySelector("svg") && btn.closest("section")
      );
      if (pencilButton) fireEvent.click(pencilButton);

      // Change username
      const usernameInput = screen.getByDisplayValue("testuser");
      fireEvent.change(usernameInput, { target: { value: "newname" } });

      // Click Save
      fireEvent.click(screen.getByRole("button", { name: /save/i }));

      await waitFor(() => {
        expect(mockApiPatch).toHaveBeenCalledWith("/users/me", {
          username: "newname",
          display_name: "Test User",
          bio: "I love studying",
        });
      });

      expect(mockSetUser).toHaveBeenCalledWith(updatedProfile);
    });

    it("cancels editing and reverts changes", () => {
      render(<ProfilePage />);

      // Enter edit mode
      const editButtons = screen.getAllByRole("button");
      const pencilButton = editButtons.find(
        (btn) => btn.querySelector("svg") && btn.closest("section")
      );
      if (pencilButton) fireEvent.click(pencilButton);

      // Change username
      const usernameInput = screen.getByDisplayValue("testuser");
      fireEvent.change(usernameInput, { target: { value: "changed" } });

      // Click Cancel
      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

      // Should show original display (not edit mode)
      expect(screen.getByText("Test User")).toBeInTheDocument();
      expect(screen.getByText("@testuser")).toBeInTheDocument();
    });
  });

  // ── Stats Section ───────────────────────────────────────────────────────

  describe("Stats Section", () => {
    it("renders all stat cards", () => {
      render(<ProfilePage />);

      expect(screen.getByText("Your Stats")).toBeInTheDocument();
      expect(screen.getByTestId("stat-sessions")).toBeInTheDocument();
      expect(screen.getByTestId("stat-focus-minutes")).toBeInTheDocument();
      expect(screen.getByTestId("stat-current-streak")).toBeInTheDocument();
    });

    it("displays reliability badge with score", () => {
      render(<ProfilePage />);

      const badge = screen.getByTestId("reliability-badge");
      expect(badge).toHaveTextContent("92");
    });
  });

  // ── Preferences Section ─────────────────────────────────────────────────

  describe("Preferences Section", () => {
    it("renders table mode buttons", () => {
      render(<ProfilePage />);

      expect(screen.getByText("Forced Audio")).toBeInTheDocument();
      expect(screen.getByText("Quiet Mode")).toBeInTheDocument();
    });

    it("changes table mode via API", async () => {
      const updatedProfile = { ...mockUser, default_table_mode: "quiet" };
      mockApiPatch.mockResolvedValueOnce(updatedProfile);

      render(<ProfilePage />);

      fireEvent.click(screen.getByText("Quiet Mode"));

      await waitFor(() => {
        expect(mockApiPatch).toHaveBeenCalledWith("/users/me", {
          default_table_mode: "quiet",
        });
      });

      expect(mockSetUser).toHaveBeenCalledWith(updatedProfile);
    });

    it("shows email notifications as coming soon", () => {
      render(<ProfilePage />);

      expect(screen.getByText("Coming Soon")).toBeInTheDocument();
    });
  });

  // ── Account Section ─────────────────────────────────────────────────────

  describe("Account Section", () => {
    it("displays connected email", () => {
      render(<ProfilePage />);

      expect(screen.getByText("test@example.com (Google)")).toBeInTheDocument();
    });

    it("signs out on button click", async () => {
      render(<ProfilePage />);

      fireEvent.click(screen.getByRole("button", { name: /sign out/i }));

      await waitFor(() => {
        expect(mockSignOut).toHaveBeenCalled();
        expect(mockClearUser).toHaveBeenCalled();
        expect(mockPush).toHaveBeenCalledWith("/login");
      });
    });

    it("shows delete confirmation dialog", () => {
      render(<ProfilePage />);

      fireEvent.click(screen.getByRole("button", { name: /delete my account/i }));

      expect(screen.getByText(/scheduled for deletion in 30 days/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /yes, delete my account/i })).toBeInTheDocument();
    });

    it("calls delete API and signs out on confirmation", async () => {
      mockApiDelete.mockResolvedValueOnce({});

      render(<ProfilePage />);

      // Open dialog
      fireEvent.click(screen.getByRole("button", { name: /delete my account/i }));

      // Confirm deletion
      fireEvent.click(screen.getByRole("button", { name: /yes, delete my account/i }));

      await waitFor(() => {
        expect(mockApiDelete).toHaveBeenCalledWith("/users/me");
        expect(mockSignOut).toHaveBeenCalled();
        expect(mockClearUser).toHaveBeenCalled();
        expect(mockPush).toHaveBeenCalledWith("/login");
      });
    });
  });
});
