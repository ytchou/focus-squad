"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { CharacterPicker } from "@/components/character-picker";
import { DEFAULT_CHARACTER } from "@/config/pixel-rooms";

export default function OnboardingPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [pixelAvatarId, setPixelAvatarId] = useState<string>(DEFAULT_CHARACTER);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.push("/login");
        return;
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/users/me`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          username: username.toLowerCase(),
          display_name: displayName || username,
          pixel_avatar_id: pixelAvatarId,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        if (response.status === 400) {
          setError(data.detail || "Username is already taken");
          setIsLoading(false);
          return;
        }
        throw new Error(data.detail || "Failed to update profile");
      }

      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setIsLoading(false);
    }
  };

  const handleUsernameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    // Only allow lowercase letters, numbers, and underscores
    const value = e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "");
    setUsername(value);
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-lg rounded-2xl bg-card p-8 shadow-lg">
        <h1 className="mb-2 text-2xl font-semibold text-foreground">Set up your profile</h1>
        <p className="mb-6 text-primary">Choose a username and character for study sessions.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="mb-1 block text-sm font-medium text-foreground">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={handleUsernameChange}
              className="w-full rounded-lg border border-accent bg-input px-4 py-2 text-foreground focus:border-primary focus:outline-none"
              placeholder="your_username"
              minLength={3}
              maxLength={30}
              required
            />
            <p className="mt-1 text-xs text-primary">Letters, numbers, and underscores only</p>
          </div>

          <div>
            <label htmlFor="displayName" className="mb-1 block text-sm font-medium text-foreground">
              Display Name (optional)
            </label>
            <input
              id="displayName"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full rounded-lg border border-accent bg-input px-4 py-2 text-foreground focus:border-primary focus:outline-none"
              placeholder="How you want to be called"
              maxLength={50}
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">
              Choose Your Character
            </label>
            <CharacterPicker selectedId={pixelAvatarId} onSelect={setPixelAvatarId} />
          </div>

          {error && (
            <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
          )}

          <button
            type="submit"
            disabled={isLoading || username.length < 3}
            className="w-full rounded-full bg-primary py-3 text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
          >
            {isLoading ? "Saving..." : "Continue"}
          </button>
        </form>
      </div>
    </div>
  );
}
