"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Clock, Flame, Users, Pencil, Check, X, LogOut, Trash2, Mic, MicOff } from "lucide-react";
import { AppShell } from "@/components/layout";
import { StatCard } from "@/components/ui/stat-card";
import { ReliabilityBadge } from "@/components/ui/reliability-badge";
import { CharacterPicker } from "@/components/character-picker";
import { PIXEL_CHARACTERS } from "@/config/pixel-rooms";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useUserStore, type UserProfile } from "@/stores/user-store";
import { api, ApiError } from "@/lib/api/client";
import { createClient } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";

// ─── Identity Section ───────────────────────────────────────────────────────

function IdentitySection({ user }: { user: UserProfile }) {
  const [isEditing, setIsEditing] = useState(false);
  const [showCharPicker, setShowCharPicker] = useState(false);
  const [username, setUsername] = useState(user.username);
  const [displayName, setDisplayName] = useState(user.display_name || "");
  const [bio, setBio] = useState(user.bio || "");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const char = user.pixel_avatar_id ? PIXEL_CHARACTERS[user.pixel_avatar_id] : null;

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const profile = await api.patch<UserProfile>("/users/me", {
        username: username.toLowerCase(),
        display_name: displayName || username,
        bio: bio || null,
      });
      useUserStore.getState().setUser(profile);
      setIsEditing(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError("Username is already taken");
      } else {
        setError("Failed to save changes");
      }
    } finally {
      setIsSaving(false);
    }
  };

  const handleCharacterChange = async (charId: string) => {
    try {
      const profile = await api.patch<UserProfile>("/users/me", {
        pixel_avatar_id: charId,
      });
      useUserStore.getState().setUser(profile);
      setShowCharPicker(false);
    } catch {
      // Silently fail — character change is non-critical
    }
  };

  const handleCancel = () => {
    setUsername(user.username);
    setDisplayName(user.display_name || "");
    setBio(user.bio || "");
    setError(null);
    setIsEditing(false);
  };

  return (
    <section className="rounded-2xl bg-card p-6 shadow-sm">
      <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
        {/* Avatar */}
        <div className="flex flex-col items-center gap-2">
          {char ? (
            <div
              className="h-24 w-24 sm:h-32 sm:w-32"
              style={{
                backgroundImage: `url(${char.spriteSheet})`,
                backgroundRepeat: "no-repeat",
                backgroundPositionY: -(char.states.working.row * char.frameHeight),
                backgroundSize: `${char.frameWidth * char.states.working.frames}px auto`,
                animation: `sprite-walk-${char.states.working.frames} ${
                  char.states.working.frames / char.states.working.fps
                }s steps(${char.states.working.frames}) infinite`,
                imageRendering: "pixelated",
              }}
            />
          ) : (
            <div className="flex h-24 w-24 items-center justify-center rounded-full bg-muted sm:h-32 sm:w-32">
              <span className="text-2xl text-muted-foreground">?</span>
            </div>
          )}
          <button
            onClick={() => setShowCharPicker(true)}
            className="text-xs text-primary hover:text-foreground transition-colors"
          >
            Change Character
          </button>
        </div>

        {/* Profile Fields */}
        <div className="flex-1 w-full">
          {isEditing ? (
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  Username
                </label>
                <input
                  value={username}
                  onChange={(e) =>
                    setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""))
                  }
                  className="w-full rounded-lg border border-accent bg-input px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none"
                  minLength={3}
                  maxLength={30}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  Display Name
                </label>
                <input
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full rounded-lg border border-accent bg-input px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none"
                  maxLength={50}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">Bio</label>
                <textarea
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                  className="w-full rounded-lg border border-accent bg-input px-3 py-1.5 text-sm text-foreground focus:border-primary focus:outline-none resize-none"
                  rows={2}
                  maxLength={160}
                  placeholder="What brings you here?"
                />
                <p className="mt-0.5 text-xs text-muted-foreground">{bio.length}/160</p>
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <div className="flex gap-2">
                <Button size="sm" onClick={handleSave} disabled={isSaving || username.length < 3}>
                  <Check className="mr-1 h-3.5 w-3.5" />
                  {isSaving ? "Saving..." : "Save"}
                </Button>
                <Button size="sm" variant="ghost" onClick={handleCancel}>
                  <X className="mr-1 h-3.5 w-3.5" />
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-semibold text-foreground">
                  {user.display_name || user.username}
                </h2>
                <button
                  onClick={() => setIsEditing(true)}
                  className="p-1 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Pencil className="h-4 w-4" />
                </button>
              </div>
              <p className="text-sm text-muted-foreground">@{user.username}</p>
              {user.bio && <p className="mt-2 text-sm text-foreground">{user.bio}</p>}
            </div>
          )}
        </div>
      </div>

      {/* Character Picker Dialog */}
      <Dialog open={showCharPicker} onOpenChange={setShowCharPicker}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Change Character</DialogTitle>
          </DialogHeader>
          <CharacterPicker selectedId={user.pixel_avatar_id} onSelect={handleCharacterChange} />
        </DialogContent>
      </Dialog>
    </section>
  );
}

// ─── Stats Section ──────────────────────────────────────────────────────────

function StatsSection({ user }: { user: UserProfile }) {
  return (
    <section>
      <h2 className="mb-3 text-lg font-semibold text-foreground">Your Stats</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard title="Sessions" value={user.session_count} icon={Users} />
        <StatCard title="Focus Minutes" value={user.total_focus_minutes} icon={Clock} />
        <StatCard
          title="Current Streak"
          value={user.current_streak}
          icon={Flame}
          subtitle={user.longest_streak > 0 ? `Best: ${user.longest_streak}` : undefined}
        />
        <div className="flex flex-col items-center justify-center rounded-xl bg-card p-4 shadow-sm">
          <p className="mb-2 text-sm font-medium text-muted-foreground">Reliability</p>
          <ReliabilityBadge score={Number(user.reliability_score)} size="lg" />
        </div>
      </div>
    </section>
  );
}

// ─── Preferences Section ────────────────────────────────────────────────────

function PreferencesSection({ user }: { user: UserProfile }) {
  const [tableMode, setTableMode] = useState(user.default_table_mode);
  const [pushEnabled, setPushEnabled] = useState(user.push_notifications_enabled);

  const handleTableModeChange = async (mode: "forced_audio" | "quiet") => {
    setTableMode(mode);
    try {
      const profile = await api.patch<UserProfile>("/users/me", {
        default_table_mode: mode,
      });
      useUserStore.getState().setUser(profile);
    } catch {
      setTableMode(user.default_table_mode); // Revert on error
    }
  };

  const handlePushToggle = async () => {
    const newValue = !pushEnabled;
    setPushEnabled(newValue);
    try {
      const profile = await api.patch<UserProfile>("/users/me", {
        push_notifications_enabled: newValue,
      });
      useUserStore.getState().setUser(profile);
    } catch {
      setPushEnabled(!newValue); // Revert on error
    }
  };

  return (
    <section className="rounded-2xl bg-card p-6 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-foreground">Preferences</h2>

      <div className="space-y-4">
        {/* Default Table Mode */}
        <div>
          <label className="mb-2 block text-sm font-medium text-foreground">
            Default Table Mode
          </label>
          <div className="flex gap-3">
            <button
              onClick={() => handleTableModeChange("forced_audio")}
              className={cn(
                "flex items-center gap-2 rounded-xl border-2 px-4 py-2.5 text-sm font-medium transition-all",
                tableMode === "forced_audio"
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border text-muted-foreground hover:border-primary/50"
              )}
            >
              <Mic className="h-4 w-4" />
              Forced Audio
            </button>
            <button
              onClick={() => handleTableModeChange("quiet")}
              className={cn(
                "flex items-center gap-2 rounded-xl border-2 px-4 py-2.5 text-sm font-medium transition-all",
                tableMode === "quiet"
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border text-muted-foreground hover:border-primary/50"
              )}
            >
              <MicOff className="h-4 w-4" />
              Quiet Mode
            </button>
          </div>
        </div>

        {/* Ambient Mix */}
        <div>
          <label className="block text-sm font-medium text-foreground">Ambient Sound Mix</label>
          <p className="text-sm text-muted-foreground">
            Managed per-session from the session controls.
          </p>
        </div>

        {/* Notifications */}
        <div>
          <label className="block text-sm font-medium text-foreground">Notifications</label>
          <div className="mt-2 space-y-2">
            <label className="flex items-center justify-between">
              <span className="text-sm text-foreground">Email Notifications</span>
              <span className="text-xs text-muted-foreground">Coming Soon</span>
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-sm text-foreground">Push Notifications</span>
              <button
                onClick={handlePushToggle}
                className={cn(
                  "relative h-6 w-11 rounded-full transition-colors",
                  pushEnabled ? "bg-primary" : "bg-muted"
                )}
              >
                <span
                  className={cn(
                    "absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white transition-transform shadow-sm",
                    pushEnabled && "translate-x-5"
                  )}
                />
              </button>
            </label>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── Account Section (Danger Zone) ──────────────────────────────────────────

function AccountSection({ user }: { user: UserProfile }) {
  const router = useRouter();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleSignOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    useUserStore.getState().clearUser();
    router.push("/login");
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    try {
      await api.delete("/users/me");
      const supabase = createClient();
      await supabase.auth.signOut();
      useUserStore.getState().clearUser();
      router.push("/login");
    } catch {
      setIsDeleting(false);
    }
  };

  return (
    <section className="rounded-2xl bg-card p-6 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-foreground">Account</h2>

      <div className="space-y-4">
        {/* Connected Account */}
        <div>
          <label className="block text-sm font-medium text-foreground">Connected Account</label>
          <p className="text-sm text-muted-foreground">{user.email} (Google)</p>
        </div>

        {/* Sign Out */}
        <Button variant="outline" onClick={handleSignOut} className="gap-2">
          <LogOut className="h-4 w-4" />
          Sign Out
        </Button>

        {/* Danger Zone */}
        <div className="mt-4 rounded-xl border-2 border-destructive/30 p-4">
          <h3 className="text-sm font-medium text-destructive">Danger Zone</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Deleting your account is scheduled with a 30-day grace period. You can sign back in to
            cancel.
          </p>
          <Button
            variant="destructive"
            size="sm"
            className="mt-3 gap-2"
            onClick={() => setShowDeleteConfirm(true)}
          >
            <Trash2 className="h-4 w-4" />
            Delete My Account
          </Button>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete Account</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Your account will be scheduled for deletion in 30 days. During this period, you can sign
            back in to cancel the deletion. After 30 days, all your data will be permanently
            removed.
          </p>
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setShowDeleteConfirm(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteAccount} disabled={isDeleting}>
              {isDeleting ? "Deleting..." : "Yes, Delete My Account"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </section>
  );
}

// ─── Profile Page ───────────────────────────────────────────────────────────

export default function ProfilePage() {
  const user = useUserStore((state) => state.user);

  if (!user) {
    return (
      <AppShell>
        <div className="flex h-64 items-center justify-center">
          <p className="text-muted-foreground">Loading profile...</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl space-y-6">
        <h1 className="text-2xl font-semibold text-foreground">Profile</h1>
        <IdentitySection user={user} />
        <StatsSection user={user} />
        <PreferencesSection user={user} />
        <AccountSection user={user} />
      </div>
    </AppShell>
  );
}
