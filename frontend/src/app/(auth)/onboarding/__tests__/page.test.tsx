import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// ─── Mocks ──────────────────────────────────────────────────────────────────

const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
}));

const mockApiPatch = vi.fn();

vi.mock("@/lib/api/client", () => ({
  api: {
    patch: (...args: unknown[]) => mockApiPatch(...args),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

// Mock CharacterPicker as a simple button that calls onSelect
vi.mock("@/components/character-picker", () => ({
  CharacterPicker: ({
    onSelect,
    selectedId,
  }: {
    onSelect: (id: string) => void;
    selectedId?: string | null;
  }) => (
    <div data-testid="character-picker">
      <span data-testid="selected-char">{selectedId}</span>
      <button data-testid="select-char-2" onClick={() => onSelect("char-2")}>
        Pick char-2
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
    "char-2": {
      id: "char-2",
      name: "Artist",
      spriteSheet: "/test2.png",
      frameWidth: 64,
      frameHeight: 64,
      states: {
        working: { frames: 4, fps: 4, row: 0 },
        speaking: { frames: 4, fps: 6, row: 1 },
        away: { frames: 3, fps: 3, row: 2 },
      },
    },
  },
  CHARACTER_IDS: ["char-1", "char-2"],
  DEFAULT_CHARACTER: "char-1",
}));

// Mock user store with getState support
const mockUserState = { user: null as null | Record<string, unknown> };
const mockSetUser = vi.fn();

vi.mock("@/stores/user-store", () => {
  const hook = () => mockUserState.user;
  return {
    useUserStore: Object.assign(hook, {
      getState: () => ({
        user: mockUserState.user,
        setUser: mockSetUser,
      }),
    }),
    type: {} as never,
  };
});

import OnboardingPage from "../page";

// ─── Tests ──────────────────────────────────────────────────────────────────

describe("OnboardingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUserState.user = null;
  });

  // ── Step 1: Welcome ─────────────────────────────────────────────────────

  describe("Step 1 - Welcome", () => {
    it("renders welcome screen with tagline and CTA", () => {
      render(<OnboardingPage />);

      expect(screen.getByText("Welcome to Focus Squad")).toBeInTheDocument();
      expect(screen.getByText("Your cozy corner for getting things done.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /let's get started/i })).toBeInTheDocument();
    });

    it("navigates to step 2 on CTA click", () => {
      render(<OnboardingPage />);

      fireEvent.click(screen.getByRole("button", { name: /let's get started/i }));

      expect(screen.getByText("Set up your profile")).toBeInTheDocument();
    });
  });

  // ── Step 2: Profile ─────────────────────────────────────────────────────

  describe("Step 2 - Profile", () => {
    function goToStep2() {
      render(<OnboardingPage />);
      fireEvent.click(screen.getByRole("button", { name: /let's get started/i }));
    }

    it("shows username, display name, and character picker", () => {
      goToStep2();

      expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/display name/i)).toBeInTheDocument();
      expect(screen.getByTestId("character-picker")).toBeInTheDocument();
    });

    it("back button returns to step 1", () => {
      goToStep2();

      fireEvent.click(screen.getByRole("button", { name: /back/i }));

      expect(screen.getByText("Welcome to Focus Squad")).toBeInTheDocument();
    });

    it("next button is enabled when username >= 3 chars (avatar defaults to char-1)", () => {
      goToStep2();

      const nextBtn = screen.getByRole("button", { name: /next/i });
      expect(nextBtn).toBeDisabled();

      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: "abc" },
      });

      expect(nextBtn).not.toBeDisabled();
    });

    it("sanitizes username to lowercase alphanumeric + underscore", () => {
      goToStep2();

      const input = screen.getByLabelText(/username/i);
      fireEvent.change(input, { target: { value: "Hello World!@#" } });

      expect(input).toHaveValue("helloworld");
    });

    it("navigates to step 3 when valid", () => {
      goToStep2();

      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: "testuser" },
      });
      fireEvent.click(screen.getByRole("button", { name: /next/i }));

      expect(screen.getByText("House Rules")).toBeInTheDocument();
    });
  });

  // ── Step 3: House Rules ─────────────────────────────────────────────────

  describe("Step 3 - House Rules", () => {
    function goToStep3() {
      render(<OnboardingPage />);
      fireEvent.click(screen.getByRole("button", { name: /let's get started/i }));
      fireEvent.change(screen.getByLabelText(/username/i), {
        target: { value: "testuser" },
      });
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
    }

    it("renders house rules with 3 norm cards", () => {
      goToStep3();

      expect(screen.getByText("Stay Focused")).toBeInTheDocument();
      expect(screen.getByText("Be Kind")).toBeInTheDocument();
      expect(screen.getByText("Stay Accountable")).toBeInTheDocument();
    });

    it("back button returns to step 2", () => {
      goToStep3();

      fireEvent.click(screen.getByRole("button", { name: /back/i }));

      expect(screen.getByText("Set up your profile")).toBeInTheDocument();
    });

    it("submit button is disabled until checkbox is checked", () => {
      goToStep3();

      const submitBtn = screen.getByRole("button", { name: /i'm in/i });
      expect(submitBtn).toBeDisabled();

      fireEvent.click(screen.getByRole("checkbox"));
      expect(submitBtn).not.toBeDisabled();
    });

    it("calls API with correct payload on submit", async () => {
      const mockProfile = { is_onboarded: true, username: "testuser" };
      mockApiPatch.mockResolvedValueOnce(mockProfile);

      goToStep3();
      fireEvent.click(screen.getByRole("checkbox"));
      fireEvent.click(screen.getByRole("button", { name: /i'm in/i }));

      await waitFor(() => {
        expect(mockApiPatch).toHaveBeenCalledWith("/users/me", {
          username: "testuser",
          display_name: "testuser",
          pixel_avatar_id: "char-1",
          is_onboarded: true,
        });
      });

      expect(mockSetUser).toHaveBeenCalledWith(mockProfile);
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });

    it("returns to step 2 on username conflict (400)", async () => {
      const { ApiError } = await import("@/lib/api/client");
      mockApiPatch.mockRejectedValueOnce(new ApiError("Conflict", 400));

      goToStep3();
      fireEvent.click(screen.getByRole("checkbox"));
      fireEvent.click(screen.getByRole("button", { name: /i'm in/i }));

      // Should navigate back to step 2 (profile form) so user can fix username
      await waitFor(() => {
        expect(screen.getByText("Set up your profile")).toBeInTheDocument();
      });

      // Username input should still have the previous value
      expect(screen.getByLabelText(/username/i)).toHaveValue("testuser");
    });
  });

  // ── Guard: already-onboarded user ───────────────────────────────────────

  describe("Guard", () => {
    it("redirects to dashboard if user is already onboarded", () => {
      mockUserState.user = { is_onboarded: true };

      render(<OnboardingPage />);

      expect(mockReplace).toHaveBeenCalledWith("/dashboard");
    });
  });
});
