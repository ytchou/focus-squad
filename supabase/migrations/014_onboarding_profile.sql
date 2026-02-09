-- Phase 3D: Onboarding Flow & Profile Page
-- Adds onboarding gate, table mode preference, and soft-delete support

-- Onboarding gate: new users must complete the wizard before accessing the app
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_onboarded BOOLEAN DEFAULT FALSE;

-- User preference for default table mode when joining sessions
ALTER TABLE users ADD COLUMN IF NOT EXISTS default_table_mode TEXT DEFAULT 'forced_audio'
  CHECK (default_table_mode IN ('forced_audio', 'quiet'));

-- Soft-delete support: 30-day grace period before actual data purge
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deletion_scheduled_at TIMESTAMPTZ;

-- Backfill: existing users who already completed onboarding (picked an avatar)
UPDATE users SET is_onboarded = TRUE WHERE pixel_avatar_id IS NOT NULL;
