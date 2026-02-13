import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { LanguageToggle } from "../language-toggle";

// Mock next/navigation
const mockRefresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: mockRefresh,
  }),
}));

// Mock next-intl (override the global mock for useLocale)
let mockLocale = "en";
vi.mock("next-intl", () => ({
  useLocale: () => mockLocale,
  useTranslations: () => (key: string) => key,
}));

// Mock api client
const mockApiPatch = vi.fn();
vi.mock("@/lib/api/client", () => ({
  api: {
    patch: (...args: unknown[]) => mockApiPatch(...args),
  },
}));

// Mock user store
const mockSetUser = vi.fn();
const mockUser = {
  id: "user-1",
  auth_id: "auth-1",
  email: "test@example.com",
  username: "testuser",
  display_name: "Test User",
  preferred_language: "en",
};
vi.mock("@/stores/user-store", () => ({
  useUserStore: {
    getState: () => ({
      user: mockUser,
      setUser: mockSetUser,
    }),
  },
}));

describe("LanguageToggle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocale = "en";
    // Clear document.cookie
    document.cookie = "NEXT_LOCALE=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
  });

  it("renders segmented toggle by default (shows EN and 繁中 buttons)", () => {
    render(<LanguageToggle />);

    expect(screen.getByRole("button", { name: "EN" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "繁中" })).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("renders dropdown variant (shows select element)", () => {
    render(<LanguageToggle variant="dropdown" />);

    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "English" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "繁體中文" })).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("highlights current locale in segmented", () => {
    render(<LanguageToggle />);

    const enButton = screen.getByRole("button", { name: "EN" });
    const zhButton = screen.getByRole("button", { name: "繁中" });

    // EN is current locale, should have highlight class
    expect(enButton).toHaveClass("bg-primary");
    expect(enButton).toHaveClass("text-white");
    // zh-TW should not be highlighted
    expect(zhButton).not.toHaveClass("bg-primary");
  });

  it("sets cookie on locale change", async () => {
    mockApiPatch.mockResolvedValueOnce({});
    render(<LanguageToggle />);

    const zhButton = screen.getByRole("button", { name: "繁中" });
    fireEvent.click(zhButton);

    await waitFor(() => {
      expect(document.cookie).toContain("NEXT_LOCALE=zh-TW");
    });
  });

  it("calls router.refresh on change", async () => {
    mockApiPatch.mockResolvedValueOnce({});
    render(<LanguageToggle />);

    const zhButton = screen.getByRole("button", { name: "繁中" });
    fireEvent.click(zhButton);

    await waitFor(() => {
      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  it("skips API call when skipApi is true", async () => {
    render(<LanguageToggle skipApi />);

    const zhButton = screen.getByRole("button", { name: "繁中" });
    fireEvent.click(zhButton);

    await waitFor(() => {
      expect(mockRefresh).toHaveBeenCalled();
    });

    // API should not be called
    expect(mockApiPatch).not.toHaveBeenCalled();
  });

  it("does nothing when clicking current locale", async () => {
    render(<LanguageToggle />);

    const enButton = screen.getByRole("button", { name: "EN" });
    fireEvent.click(enButton);

    // Wait a bit to ensure nothing happens
    await new Promise((resolve) => setTimeout(resolve, 50));

    // Nothing should change
    expect(mockRefresh).not.toHaveBeenCalled();
    expect(mockApiPatch).not.toHaveBeenCalled();
  });
});
