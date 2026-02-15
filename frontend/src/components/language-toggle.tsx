"use client";

import { useRouter } from "next/navigation";
import { useLocale } from "next-intl";
import { api } from "@/lib/api/client";
import { useUserStore } from "@/stores/user-store";
import { trackLanguageSwitched } from "@/lib/posthog/events";

type Locale = "en" | "zh-TW";

interface LanguageToggleProps {
  variant?: "segmented" | "dropdown";
  /** Skip the API call (e.g., during onboarding before user is fully created) */
  skipApi?: boolean;
}

function setLocaleCookie(locale: Locale) {
  document.cookie = `NEXT_LOCALE=${locale};path=/;max-age=31536000;SameSite=Lax`;
}

export function LanguageToggle({ variant = "segmented", skipApi = false }: LanguageToggleProps) {
  const currentLocale = useLocale() as Locale;
  const router = useRouter();

  async function handleChange(newLocale: Locale) {
    if (newLocale === currentLocale) return;

    trackLanguageSwitched(currentLocale, newLocale);
    setLocaleCookie(newLocale);

    // Update user profile in DB (fire-and-forget unless skipApi)
    if (!skipApi) {
      try {
        await api.patch("/users/me", { preferred_language: newLocale });
        const user = useUserStore.getState().user;
        if (user) {
          useUserStore.getState().setUser({ ...user, preferred_language: newLocale });
        }
      } catch {
        // Non-critical: cookie is already set, preference persists locally
      }
    }

    router.refresh();
  }

  if (variant === "dropdown") {
    return (
      <select
        value={currentLocale}
        onChange={(e) => handleChange(e.target.value as Locale)}
        className="rounded-xl border border-border bg-surface px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
      >
        <option value="en">English</option>
        <option value="zh-TW">繁體中文</option>
      </select>
    );
  }

  // Segmented toggle
  return (
    <div className="inline-flex items-center rounded-xl border border-border bg-surface-alt text-sm">
      <button
        type="button"
        onClick={() => handleChange("en")}
        className={`rounded-l-xl px-3 py-1.5 font-medium transition-colors ${
          currentLocale === "en" ? "bg-primary text-white" : "text-muted hover:text-foreground"
        }`}
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => handleChange("zh-TW")}
        className={`rounded-r-xl px-3 py-1.5 font-medium transition-colors ${
          currentLocale === "zh-TW" ? "bg-primary text-white" : "text-muted hover:text-foreground"
        }`}
      >
        繁中
      </button>
    </div>
  );
}
