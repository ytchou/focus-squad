"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Target, Heart, Shield, ArrowLeft } from "lucide-react";
import { useTranslations, useLocale } from "next-intl";
import { CharacterPicker } from "@/components/character-picker";
import { LanguageToggle } from "@/components/language-toggle";
import { PIXEL_CHARACTERS, CHARACTER_IDS, DEFAULT_CHARACTER } from "@/config/pixel-rooms";
import { api, ApiError } from "@/lib/api/client";
import { useUserStore, type UserProfile } from "@/stores/user-store";

const STEPS = [1, 2, 3] as const;

function ProgressDots({ current }: { current: number }) {
  return (
    <div className="flex justify-center gap-2 mb-8">
      {STEPS.map((step) => (
        <div
          key={step}
          className={`h-2 w-2 rounded-full transition-colors ${
            step === current ? "bg-primary" : "bg-muted"
          }`}
        />
      ))}
    </div>
  );
}

function WelcomeStep({ onNext }: { onNext: () => void }) {
  const t = useTranslations("onboarding");
  const locale = useLocale();
  // Show a few character previews decoratively
  const previewChars = CHARACTER_IDS.slice(0, 4);

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-gradient-to-b from-surface to-background">
      {/* Language toggle — top right */}
      <div className="absolute right-4 top-4">
        <LanguageToggle variant="segmented" skipApi />
      </div>

      <div className="w-full max-w-lg px-6 text-center">
        <ProgressDots current={1} />

        {/* Decorative character sprites */}
        <div className="mb-8 flex justify-center gap-6">
          {previewChars.map((id) => {
            const char = PIXEL_CHARACTERS[id];
            return (
              <div
                key={id}
                className="h-16 w-16"
                style={{
                  backgroundImage: `url(${char.spriteSheet})`,
                  backgroundRepeat: "no-repeat",
                  backgroundPositionY: -(char.states.working.row * char.frameHeight),
                  animation: `sprite-walk-${char.states.working.frames} ${
                    char.states.working.frames / char.states.working.fps
                  }s steps(${char.states.working.frames}) infinite`,
                  imageRendering: "pixelated",
                }}
              />
            );
          })}
        </div>

        <h1 className="mb-3 text-3xl font-semibold text-foreground">{t("welcome")}</h1>
        <p className="mb-8 text-lg text-primary">{t("welcomeSubtitle")}</p>

        <button
          onClick={onNext}
          className="w-full max-w-xs rounded-full bg-primary py-3 text-primary-foreground transition-colors hover:bg-primary/90"
        >
          {t("letsGetStarted")}
        </button>

        {/* Bilingual hint — always in the opposite language */}
        <p className="mt-4 text-sm text-muted">
          {locale === "en" ? t("languageHintEn") : t("languageHintZhTW")}
        </p>
      </div>
    </div>
  );
}

function ProfileStep({
  username,
  displayName,
  pixelAvatarId,
  onUsernameChange,
  onDisplayNameChange,
  onAvatarSelect,
  onNext,
  onBack,
}: {
  username: string;
  displayName: string;
  pixelAvatarId: string;
  onUsernameChange: (value: string) => void;
  onDisplayNameChange: (value: string) => void;
  onAvatarSelect: (id: string) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const t = useTranslations("onboarding");
  const tc = useTranslations("common");
  const canProceed = username.length >= 3 && pixelAvatarId;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-lg rounded-2xl bg-card p-8 shadow-lg">
        <ProgressDots current={2} />

        <button
          onClick={onBack}
          className="mb-4 flex items-center gap-1 text-sm text-primary hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          {tc("back")}
        </button>

        <h1 className="mb-2 text-2xl font-semibold text-foreground">{t("profileSetup")}</h1>
        <p className="mb-6 text-primary">{t("profileSubtitle")}</p>

        <div className="space-y-4">
          <div>
            <label htmlFor="username" className="mb-1 block text-sm font-medium text-foreground">
              {t("username")}
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => {
                const value = e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "");
                onUsernameChange(value);
              }}
              className="w-full rounded-lg border border-accent bg-input px-4 py-2 text-foreground focus:border-primary focus:outline-none"
              placeholder={t("usernamePlaceholder")}
              minLength={3}
              maxLength={30}
              required
            />
            <p className="mt-1 text-xs text-primary">{t("usernameHint")}</p>
          </div>

          <div>
            <label htmlFor="displayName" className="mb-1 block text-sm font-medium text-foreground">
              {t("displayName")}
            </label>
            <input
              id="displayName"
              type="text"
              value={displayName}
              onChange={(e) => onDisplayNameChange(e.target.value)}
              className="w-full rounded-lg border border-accent bg-input px-4 py-2 text-foreground focus:border-primary focus:outline-none"
              placeholder={t("displayNamePlaceholder")}
              maxLength={50}
            />
            <p className="mt-1 text-xs text-primary">{t("displayNameOptional")}</p>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">
              {t("chooseCharacter")}
            </label>
            <CharacterPicker selectedId={pixelAvatarId} onSelect={onAvatarSelect} />
          </div>

          <button
            onClick={onNext}
            disabled={!canProceed}
            className="w-full rounded-full bg-primary py-3 text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            {tc("next")}
          </button>
        </div>
      </div>
    </div>
  );
}

function HouseRulesStep({
  onSubmit,
  onBack,
  isLoading,
  error,
}: {
  onSubmit: () => void;
  onBack: () => void;
  isLoading: boolean;
  error: string | null;
}) {
  const t = useTranslations("onboarding");
  const tc = useTranslations("common");
  const [agreed, setAgreed] = useState(false);

  const houseRules = [
    {
      icon: Target,
      titleKey: "stayFocused" as const,
      descKey: "stayFocusedDesc" as const,
    },
    {
      icon: Heart,
      titleKey: "beKind" as const,
      descKey: "beKindDesc" as const,
    },
    {
      icon: Shield,
      titleKey: "stayAccountable" as const,
      descKey: "stayAccountableDesc" as const,
    },
  ];

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-lg rounded-2xl bg-card p-8 shadow-lg">
        <ProgressDots current={3} />

        <button
          onClick={onBack}
          className="mb-4 flex items-center gap-1 text-sm text-primary hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          {tc("back")}
        </button>

        <h1 className="mb-2 text-2xl font-semibold text-foreground">{t("houseRules")}</h1>
        <p className="mb-6 text-primary">{t("houseRulesSubtitle")}</p>

        <div className="space-y-3 mb-6">
          {houseRules.map((rule) => (
            <div
              key={rule.titleKey}
              className="flex items-start gap-3 rounded-xl bg-surface p-4 shadow-sm"
            >
              <rule.icon className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
              <div>
                <h3 className="font-medium text-foreground">{t(rule.titleKey)}</h3>
                <p className="text-sm text-primary">{t(rule.descKey)}</p>
              </div>
            </div>
          ))}
        </div>

        <label className="mb-6 flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            className="h-4 w-4 rounded border-accent text-primary focus:ring-primary"
          />
          <span className="text-sm text-foreground">{t("agreeToNorms")}</span>
        </label>

        {error && (
          <div className="mb-4 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <button
          onClick={onSubmit}
          disabled={!agreed || isLoading}
          className="w-full rounded-full bg-primary py-3 text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          {isLoading ? t("saving") : t("imIn")}
        </button>
      </div>
    </div>
  );
}

export default function OnboardingPage() {
  const router = useRouter();
  const t = useTranslations("onboarding");
  const [step, setStep] = useState(1);
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [pixelAvatarId, setPixelAvatarId] = useState<string>(DEFAULT_CHARACTER);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Guard: if user is already onboarded, redirect to dashboard
  useEffect(() => {
    const user = useUserStore.getState().user;
    if (user?.is_onboarded) {
      router.replace("/dashboard");
    }
  }, [router]);

  const handleSubmit = async () => {
    setError(null);
    setIsLoading(true);

    try {
      const profile = await api.patch<UserProfile>("/users/me", {
        username: username.toLowerCase(),
        display_name: displayName || username,
        pixel_avatar_id: pixelAvatarId,
        is_onboarded: true,
      });

      useUserStore.getState().setUser(profile);
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 400) {
          setError(t("usernameTaken"));
          setStep(2); // Go back to profile step
        } else {
          setError(err.message);
        }
      } else {
        setError(t("somethingWentWrong"));
      }
      setIsLoading(false);
    }
  };

  if (step === 1) {
    return <WelcomeStep onNext={() => setStep(2)} />;
  }

  if (step === 2) {
    return (
      <ProfileStep
        username={username}
        displayName={displayName}
        pixelAvatarId={pixelAvatarId}
        onUsernameChange={setUsername}
        onDisplayNameChange={setDisplayName}
        onAvatarSelect={setPixelAvatarId}
        onNext={() => setStep(3)}
        onBack={() => setStep(1)}
      />
    );
  }

  return (
    <HouseRulesStep
      onSubmit={handleSubmit}
      onBack={() => setStep(2)}
      isLoading={isLoading}
      error={error}
    />
  );
}
