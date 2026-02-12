# Focus Squad - Development TODO

> Track progress by checking off tasks as completed. Add new tasks as discovered.

## Legend
- [ ] Not started
- [x] Completed
- 🚧 In progress

---

## Phase 1: Foundation (Week 1-2)

### Backend Infrastructure
- [x] Set up Supabase project and run initial migration
- [x] Configure environment variables (.env from .env.example)
- [x] Implement Supabase Auth integration in FastAPI
- [x] Create JWT validation middleware
- [x] Set up Redis connection for session state

### Schema Enhancements
- [x] Create migration `002_user_service_tables.sql`
- [x] Add `notification_preferences` table (user_id, event_type, email_enabled, push_enabled)
- [x] Add `essence_transactions` table (user_id, amount, transaction_type, related_session_id)
- [x] Add missing indexes for performance:
  - [x] `CREATE INDEX idx_users_auth_id ON users(auth_id)` - critical for auth mapping
  - [x] `CREATE INDEX idx_credit_transactions_user ON credit_transactions(user_id)`
  - [x] `CREATE INDEX idx_ratings_created ON ratings(created_at)` - for time-decay queries
- [x] Run migration in Supabase

### User System (Backend)
- [x] Create Pydantic models (`backend/app/models/user.py`)
  - [x] `UserProfile` (full profile for authenticated user)
  - [x] `UserPublicProfile` (limited fields for other users)
  - [x] `UserProfileUpdate` (partial update model)
- [x] Create `UserService` (`backend/app/services/user_service.py`)
  - [x] `get_user_by_auth_id()` - Fetch user from Supabase
  - [x] `create_user_if_not_exists()` - Upsert for first OAuth login
  - [x] `update_user_profile()` - Patch profile fields
  - [x] `get_public_profile()` - Public profile for other users
  - [x] Auto-generate username from email with collision handling
  - [x] Auto-create associated records (credits, essence, notification_preferences)
- [x] Wire up router endpoints (`backend/app/routers/users.py`)
  - [x] `GET /api/v1/users/me` - Return full profile (upsert on first call)
  - [x] `PATCH /api/v1/users/me` - Update profile with conflict handling
  - [x] `GET /api/v1/users/{user_id}` - Return public profile

### Authentication (Frontend)
- [x] Configure NextAuth with Google OAuth provider
  - Note: Used Supabase Auth directly instead of NextAuth for simpler integration with backend JWT validation
- [x] Create auth middleware for protected routes
- [x] Build login page with Google OAuth button
- [x] Build onboarding flow (username selection)
- [x] Set up Supabase client (SSR-compatible)

### Frontend Foundation
- [x] Configure Tailwind with design tokens in globals.css
  - [x] Add earth-tone color palette (background, surface, primary, accent, etc.)
  - [x] Configure @theme inline for Tailwind v4
  - [x] Add radius and shadow variables
- [x] Set up shadcn/ui component library
  - [x] Install dependencies (class-variance-authority, clsx, tailwind-merge)
  - [x] Create lib/utils.ts with cn() function
  - [x] Create components.json configuration
  - [x] Add core components (Button, Card, Input, Badge, Avatar, Dialog, Sonner, etc.)
- [x] Create custom UI components
  - [x] StatCard (dashboard stats)
  - [x] CreditBadge (credit display)
  - [x] ReliabilityBadge (user reliability indicator)
- [x] Set up Zustand stores (extended scope)
  - [x] user-store.ts (already exists)
  - [x] ui-store.ts (sidebar, modal, theme)
  - [x] session-store.ts (phase, timer, tableId, participants)
  - [x] credits-store.ts (balance, tier, weeklyUsed)
  - [x] notifications-store.ts (notifications array)
  - [x] stores/index.ts (barrel export)
- [x] Create base layout components
  - [x] AppShell (main wrapper)
  - [x] Header (top bar with logo, credits, user menu)
  - [x] Sidebar (collapsible navigation)
- [x] Migrate existing pages to use design tokens
  - [x] login/page.tsx
  - [x] onboarding/page.tsx
  - [x] dashboard/page.tsx
  - [x] login-button.tsx, logout-button.tsx

### Testing Foundation
- [x] Set up pytest with async support (backend)
  - [x] Enhanced conftest.py with JWT/JWKS fixtures
  - [x] Added cryptography dependency for RSA key generation
- [x] Write tests for auth middleware
  - [x] Unit tests for auth.py (31 tests, 100% coverage)
  - [x] Unit tests for middleware.py (14 tests, 98% coverage)
  - [x] Integration tests (9 tests)
- [x] Set up Jest/Vitest for frontend
- [x] Add store tests (credits-store, session-store)
- [x] Add CI workflow for running tests (backend-ci.yml, frontend-ci.yml exist)

---

## Phase 2: Core Loop (Week 3-4)

### Session System (Backend)
- [x] Create session Pydantic models (`backend/app/models/session.py`)
  - [x] Enums: `TableMode`, `SessionPhase`, `ParticipantType`
  - [x] Request models: `SessionFilters`, `QuickMatchRequest`, `LeaveSessionRequest`
  - [x] Response models: `ParticipantInfo`, `SessionInfo`, `QuickMatchResponse`, `UpcomingSession`
  - [x] Database models: `SessionDB`, `ParticipantDB`
- [x] Implement `SessionService` (`backend/app/services/session_service.py`)
  - [x] `calculate_next_slot()` - Find next :00/:30 time slot
  - [x] `get_session_by_id()` - Fetch session with participants
  - [x] `get_user_sessions()` - List upcoming sessions for user
  - [x] `find_matching_session()` - Find session with available seats
  - [x] `create_session()` - Create new session with LiveKit room
  - [x] `add_participant()` - Join session, assign seat (1-4)
  - [x] `remove_participant()` - Leave session early
  - [x] `add_ai_companions()` - Fill empty seats with AI
  - [x] `calculate_current_phase()` - Determine phase from elapsed time
  - [x] `generate_livekit_token()` - Create LiveKit access token
- [x] Implement `CreditService` (minimal) (`backend/app/services/credit_service.py`)
  - [x] `get_balance()` - Returns credits_remaining, tier
  - [x] `has_sufficient_credits()` - Check balance >= amount
  - [x] `deduct_credit()` - Deduct and log transaction
  - [x] `add_credit()` - Add and log transaction
- [x] Complete session router endpoints (`backend/app/routers/sessions.py`)
  - [x] `POST /api/v1/sessions/quick-match` - Quick match with credit deduction
  - [x] `GET /api/v1/sessions/upcoming` - List user's upcoming sessions
  - [x] `GET /api/v1/sessions/{session_id}` - Get session details
  - [x] `POST /api/v1/sessions/{session_id}/leave` - Leave early (no refund)
- [x] Implement session state machine (Setup → Work_1 → Break → Work_2 → Social → Ended)
- [x] Add AI companion seat filling logic
- [x] Write unit tests (TDD) with 89%+ coverage
  - [x] `test_session_service.py` - 32 tests
  - [x] `test_credit_service.py` - 8 tests

### LiveKit Integration
- [x] Implement LiveKit token generation (in SessionService)
- [x] Create LiveKit room management service (room creation/deletion)
  - [x] Add `constants.py` with timing values (grace period, room lead time, etc.)
  - [x] Create `LiveKitService` with `create_room()`, `delete_room()`, `get_room()`, `generate_token()`
  - [x] Mode-aware token generation (Forced Audio: canPublish=true, Quiet Mode: canPublish=false)
- [x] Setup Celery for scheduled tasks
  - [x] Add `celery[redis]` to requirements.txt
  - [x] Create `celery_app.py` configuration
  - [x] Create `tasks/livekit_tasks.py` (room creation at T-30s, cleanup after session)
- [x] Handle participant join/leave events (webhooks)
  - [x] Create `routers/webhooks.py` with `POST /api/v1/webhooks/livekit`
  - [x] Validate webhook signature with `WebhookReceiver`
  - [x] Handle events: participant_joined, participant_left, track_published, room_finished
  - [x] Update participant connection status in database
- [x] Implement audio-only room configuration
- [x] Add Quiet Mode (muted by default) support
- [x] Add migration for session_participants columns (connected_at, disconnected_at, is_connected)
- [x] Integrate Celery tasks with quick-match endpoint

### Credit System (Backend)
> **Design Doc:** [output/plan/2025-02-06-credit-system-redesign.md](output/plan/2025-02-06-credit-system-redesign.md)

**Completed (Foundation):**
- [x] Implement `CreditService` (minimal - balance, deduct, add)
- [x] Add credit transaction logging (in CreditService)

**Schema & Models:**
- [x] Create migration `005_credit_system_redesign.sql` (add `credit_cycle_start`, refund tracking)
- [x] Consolidate duplicate models to `backend/app/models/credit.py`

**CreditService Updates:**
- [x] Add `refund_credit(user_id, session_id)` method
- [x] Add `refresh_credits_for_user(user_id)` method (rolling 7-day, 2x cap)
- [x] Add `gift_credit(sender_id, recipient_id, amount)` method
- [x] Add `apply_referral_code(user_id, code)` method
- [x] Add `award_referral_bonus(user_id, session_id)` method
- [x] Add `get_referral_info(user_id)` method

**API Endpoints:**
- [x] Implement `GET /api/v1/credits/balance` endpoint
- [x] Implement `POST /api/v1/credits/gift` endpoint (Pro/Elite only, 4/week limit)
- [x] Implement `GET /api/v1/credits/referral` endpoint
- [x] Implement `POST /api/v1/credits/referral/apply` endpoint
- [x] Implement `POST /api/v1/sessions/{session_id}/cancel` endpoint (refund if ≥1hr before)

**Background Tasks:**
- [x] Create `backend/app/tasks/credit_tasks.py` with daily refresh task
- [x] Add Celery beat schedule (daily 00:05 UTC)

**Integration:**
- [x] Add referral award logic to session end handler
- [x] Update user onboarding to set `credit_cycle_start = CURRENT_DATE`

**Testing:**
- [x] Write unit tests for new CreditService methods (126 tests passing)
- [x] Write integration tests for credit endpoints (13 tests, 139 total passing)

### Session UI (Frontend)
- [x] Build dashboard/home page (upcoming sessions, stats) - basic version exists
- [x] Create session lobby page (waiting for match) - `/session/[sessionId]/waiting`
- [x] Build study session page with 55-min timer
  - [x] Create phase utilities (`lib/session/phase-utils.ts`)
  - [x] Build session layout components (`components/session/`)
  - [x] Build timer display with circular progress and phase indicator
  - [x] Build 4-seat table view with participant seats
- [x] Implement LiveKit audio integration (mute/unmute)
  - [x] Create `LiveKitRoomProvider` wrapper
  - [x] Implement `useLocalMicrophone` and `useActiveSpeakers` hooks
  - [x] Add connection status component
- [x] Add active status indicators (waveform, typing)
  - [x] Pulsing ring animation for speaking participants
  - [x] Activity tracking hook with opt-in keyboard/mouse detection
- [x] Create session end screen
  - [x] Session end modal with summary
  - [x] Session end page with stats and rating prompt

### Timer & State Sync
- [x] Implement shared Pomodoro timer (via client-side calculation from start time)
- [x] Sync session phase transitions across participants (timer hook with phase change callback)
- [x] Handle disconnect/reconnect grace period (2 min) - connection status component

### Phase 2 Completion Gaps (Blocking)
> **Implementation plan:** [Phase 2 Completion Plan](output/plan/2025-02-07-phase2-completion.md)

- [x] **[P1]** Complete WebHook handlers (`_handle_participant_left`, `_handle_room_finished`)
  - [x] Update disconnect_count and total_active_minutes on leave
  - [x] Mark session ended on room_finished
  - [x] Award essence on session completion (1 Furniture Essence per qualifying participant)
  - [x] Add `is_session_completed()` helper: present through both work blocks + 20 min active time
  - [x] Make `cleanup_ended_session` idempotent (guard on `livekit_room_deleted_at`)
- [x] **[P1]** Connect session end page to actual session data
  - [x] Add `GET /sessions/{id}/summary` endpoint (works during social phase too)
  - [x] Replace hardcoded "47 min, +1 Essence, 3 tablemates" with real API data
  - [x] Add loading state and fallback defaults
  - [x] Update SessionEndModal with optional `focusMinutes` and `essenceEarned` props

### Session System Gaps
- ~~**[P1]** Add session start validation (minimum 2 real users required)~~ **DROPPED** - Allow 1 human + 3 AI companions
- [x] **[P2]** Add phase lock to `add_participant()` - only allow joins during setup phase (via atomic RPC)
- [ ] **[P2]** ~~Implement table merging logic for sessions with <2 real users~~ **DEFERRED to Phase 3**

### Data Integrity Gaps
- [x] **[P2]** Add PostgreSQL RPC `atomic_add_participant()` (migration 009)
  - [x] FOR UPDATE row lock + phase check + seat assignment in single transaction
  - [x] Prevents race condition in concurrent joins
- [x] **[P2]** Add PostgreSQL RPC `atomic_transfer_credits()` (migration 009)
  - [x] Lean approach: SQL handles atomic money movement, Python validates business rules
  - [x] Prevents lost credits on partial failure
- [x] **[P2]** Add idempotency tokens for credit operations
  - [x] Add `idempotency_key` UUID column to credit_transactions
  - [x] Accept `X-Idempotency-Key` header in gift endpoint
  - [x] Prevent double-credits from duplicate webhook calls

### Backend Fixes
- [x] **[P2]** Fix weekly refresh to use UTC timezone
  - [x] Replace `date.today()` with `datetime.now(timezone.utc).date()` (6 locations across credit_service, user_service, credit_tasks)
  - All backend processing uses UTC; frontend converts to local for display
- [x] **[P2]** Fix referral bonus validation
  - [x] Bug: `.not_.is_("left_at", "null")` selects users who LEFT EARLY (inverted logic)
  - [x] Fix: `.is_("left_at", "null")` + use `is_session_completed()` helper
- [x] **[P3]** Add session phase progression scheduled task
  - [x] Celery beat task every 30s: update current_phase in DB for active sessions
  - [x] Schedule cleanup when session transitions to ended
- [x] **[P3]** Fix focus time calculation in livekit_tasks.py
  - [x] Replace hardcoded `focus_minutes = 45` with actual calculation
  - [x] Calculate from connected_at/disconnected_at or total_active_minutes, cap at 45

### Testing Gaps
- [x] **[P2]** Add tests for `phase-utils.ts` boundary conditions (66 tests)
  - [x] Test exact phase transitions at 0, 3, 28, 30, 50, 55 minutes
  - [x] Test edge cases (negative time, past end time, string vs Date input)
  - [x] Test formatTime, getNextPhase, isWorkPhase, getPhaseDuration
- [x] **[P3]** Add component tests for session active page (11 tests)
  - [x] Loading/error states, phase transitions, leave button, participant polling
- [x] **[P3]** Add hook tests for useSessionTimer (8 tests) and useActivityTracking (6 tests)

---

## Phase 3: Social & Polish (Week 5-6)

### Peer Review System (Backend)
> **Design Doc:** [output/plan/2026-02-08-peer-review-system.md](output/plan/2026-02-08-peer-review-system.md)

- [x] Database migration (`010_peer_review_system.sql`): pending_ratings table, reason JSONB column, indexes
- [x] Backend models (`models/rating.py`): enums, request/response models, exceptions
- [x] Constants: reliability algorithm params, ban thresholds, reporting power multipliers
- [x] `RatingService` (`services/rating_service.py`): submit, skip, calculate reliability, reporting power, penalty check
- [x] API endpoints: `POST /{session_id}/rate`, `POST /{session_id}/rate/skip`, `GET /pending-ratings`
- [x] Pending ratings soft blocker in `quick_match()` (403 if unresolved ratings)
- [x] 26 unit tests for RatingService, all passing (TDD)
- [x] Router-level auth tests for new endpoints

### Peer Review UI (Frontend)
- [x] Rating store (`stores/rating-store.ts`): Zustand store for rating state + API calls
- [x] `RatingCard` component: avatar, thumbs up/down/skip buttons, per-user
- [x] `RatingReasonsPicker`: expandable checkbox list + "Other" free text
- [x] Session end page: inline rating cards with submit/skip flow
- [x] Dashboard: pending ratings alert card with link to session end page
- [x] Banned page (`/banned`): gentle explanation + countdown timer
- [x] `ReliabilityBadge`: updated to 4-tier system (Trusted/Good/Fair/New)
- [x] Display rating history in user dashboard

### Session Board (Reflections + Chat)
> **Design Doc:** [output/plan/2026-02-08-session-board-design.md](output/plan/2026-02-08-session-board-design.md)
- [x] Design session board UI (single stream with visually distinct reflection prompts)
- [x] Implement reflection prompts at phase transitions (setup goal, mid-session check-in, end afterthoughts)
- [x] Build shared message board component (LiveKit data channels for real-time sync)
- [x] Persist reflections to DB (free-form chat is ephemeral)
- [x] Add gentle nudge notifications at phase transitions

### Session Diary
> **Design Doc:** [output/plan/2026-02-09-session-diary-design.md](output/plan/2026-02-09-session-diary-design.md)

- [x] Database migration (`012_diary_notes.sql`): diary_notes table with RLS, GIN index on tags
- [x] Backend models: `SaveDiaryNoteRequest`, `DiaryNoteResponse`, `DiaryStatsResponse`, updated `DiaryEntry`
- [x] Constants: `DIARY_TAGS` (8 predefined), `DIARY_NOTE_MAX_LENGTH = 2000`
- [x] `ReflectionService` updates: `save_diary_note()`, `get_diary_stats()`, enhanced `get_diary()` with search/date filters
- [x] API endpoints: `GET /diary` (updated with search, date_from, date_to), `GET /diary/stats`, `POST /diary/{session_id}/note`
- [x] Build personal session diary page (`/diary` route) with timeline + calendar views
- [x] 7 diary components: header, entry card, tag picker, journal editor, timeline, calendar, barrel export
- [x] Display reflection history with date, session info, phase-colored reflections, focus time, essence indicator
- [x] Add filtering/search across past reflections (debounced text search + date range)
- [x] Post-session journaling: expandable textarea + predefined tag picker (8 tags)
- [x] Calendar view with react-day-picker (session day highlighting, click-to-view)
- [x] Sidebar: added Diary link with BookOpen icon
- [x] Dashboard: renamed "View History" to "Diary", removed RatingHistoryCard
- [x] Backend tests: 9 new unit tests (service) + router test updates (21 total reflection tests)
- [x] Frontend tests: 16 component tests (DiaryEntryCard + DiaryTagPicker)

### Phase 3A: Pixel Art Visual Foundation
> **Design Doc:** [output/plan/2026-02-09-pixel-art-ui-design.md](output/plan/2026-02-09-pixel-art-ui-design.md)
> **Implementation Plan:** [output/plan/2026-02-09-pixel-art-implementation-plan.md](output/plan/2026-02-09-pixel-art-implementation-plan.md)

- [x] Source royalty-free pixel art assets from itch.io/OpenGameArt
  - 3 room backgrounds: cozy study room, coffee shop, library (isometric, 4 desk positions each)
  - 8+ character sprite sheets: distinct styles, 3 states (working/speaking/away), 3-4 frames each
  - Color-adjust assets to match design tokens (earth tones)
- [x] Create asset pipeline and room config (`frontend/src/config/pixel-rooms.ts`)
- [x] Database migration `013_pixel_art_system.sql`: `pixel_avatar_id` on users, `room_type` on sessions
- [x] Backend updates: models, services, constants for pixel avatar + room type
- [x] Add pixel design tokens to `globals.css` (`--font-pixel`, `--border-pixel`, `--shadow-pixel`)
- [x] Build `CharacterSprite` component with CSS sprite animation (steps() timing)
  - 3 states: working (4fps), speaking (6fps, 2s debounce), away (3fps)
- [x] Build `CharacterLayer` component (maps participants to sprites at desk positions)
- [x] Build `PixelRoom` background component (full viewport, object-fit cover)
- [x] Build `HudOverlay` (semi-transparent top bar: timer, phase, credits, leave)
- [x] Build `ChatPanel` (floating right panel, expands during reflection phases)
- [x] Create `PixelSessionLayout` (full-scene: room + characters + HUD + chat + controls)
- [x] Extract current layout to `ClassicSessionLayout` (preserved as fallback toggle)
- [x] Integrate pixel/classic toggle in session page (default: pixel, stored in localStorage)
- [x] Build `CharacterPicker` component (grid of 8+ animated previews)
- [x] Add character selection to onboarding flow
- [x] Tests: CharacterSprite, pixel-rooms config, CharacterPicker

### Phase 3B: Immersion Layer
> **Design Doc:** [output/plan/2026-02-09-immersion-layer-plan.md](output/plan/2026-02-09-immersion-layer-plan.md)

- [x] Ambient Sound Mixer
  - [x] Source royalty-free audio tracks (Lo-Fi, Coffee Shop, Rain) from Pixabay/Mixkit
  - [x] Trim audio files to seamless loops (~2-5 min each, MP3 128kbps)
  - [x] Create track config (`frontend/src/config/ambient-tracks.ts`)
  - [x] Build `useAmbientMixer` hook with WebAudioAPI
    - AudioBufferSourceNode → GainNode → AudioContext.destination per track
    - Independent on/off and volume control per track
    - Mixable (multiple tracks simultaneously)
    - Local-only playback (never sent to LiveKit)
    - Handle browser autoplay policy (lazy AudioContext)
  - [x] Build `AmbientMixerControls` component (3 toggle buttons + volume sliders)
  - [x] Integrate into shared ControlBar (works in pixel + classic layouts)
  - [x] Persist ambient preferences to localStorage per user
  - [x] Tests for `useAmbientMixer` hook
- [x] Activity & Presence Detection
  - [x] Create presence types (`frontend/src/types/activity.ts`): PresenceState, PresenceMessage
  - [x] Build `usePresenceDetection` hook (replaces `useActivityTracking`)
    - Page Visibility API (`visibilitychange` event)
    - Keyboard/mouse tracking (opt-in, timestamps only, privacy-first)
    - 4-state machine: ACTIVE → GRACE (2min) → AWAY (5min) → GHOSTING
    - 10s interval for state derivation, 30s periodic broadcast for late joiners
  - [x] Build `ActivityConsentPrompt` component (non-blocking card, localStorage consent)
  - [x] Integrate into session page: broadcast + receive presence via LiveKit data channel
  - [x] Update `Participant` interface: `isActive: boolean` → `presenceState: PresenceState`
  - [x] Update `ParticipantSeat` badge (Focused/Away/Gone)
  - [x] Update `ControlBar` presence indicator (dynamic green/yellow/red dot)
  - [x] Deprecate `useActivityTracking` hook
  - [x] Tests for `usePresenceDetection` hook
- [x] Character Animation Enhancement
  - [x] Update `CharacterLayer` state logic to use `presenceState`
  - [x] Add `isGhosting` prop to `CharacterSprite` (opacity: 0.4, 1s ease transition)
  - [x] Update existing CharacterSprite tests for ghosting

### Phase 3C: Picture-in-Picture Mini View
> **Design Doc:** [output/plan/2026-02-09-pip-mini-view-design.md](output/plan/2026-02-09-pip-mini-view-design.md)

- [x] TypeScript type declarations for Document PiP API (`types/document-pip.d.ts`)
- [x] Canvas PiP Renderer (`components/session/pip/pip-canvas-renderer.ts`)
  - 320x180 canvas: phase-colored timer + 4 participant circles with presence borders
  - Fallback for Safari/Firefox (static frames, system fonts)
- [x] Document PiP React component (`components/session/pip/pip-mini-view.tsx`)
  - Same layout, real React rendering for Chrome/Edge
  - All inline styles (PiP window is separate browsing context)
- [x] PiP toggle button (`components/session/pip/pip-toggle-button.tsx`) + barrel export
- [x] `usePictureInPicture` hook (`hooks/use-picture-in-picture.ts`)
  - Dual strategy: Document PiP (primary) + Canvas Video PiP (fallback)
  - Auto-close on session end, cleanup on unmount
- [x] Presence detection integration: add `isPiPActive` to `usePresenceDetection`
  - PiP open = page considered "visible" for activity
- [x] Control bar integration: add PiP toggle after ambient mixer controls
- [x] Session page wiring: PiP state flow between hook and presence detection
- [x] PixelSessionLayout: forward PiP props to ControlBar
- [x] Tests: PiP hook, PiPMiniView, PiPToggleButton
- [x] Verification: build, lint, all tests pass

### Phase 3D: Onboarding Flow & Profile Page
> **Design Doc:** [output/plan/2026-02-09-onboarding-profile-design.md]
> **Plan File:** [.claude/plans/concurrent-dancing-dove.md]

**Database Migration (`014_onboarding_profile.sql`):**
- [x] Add `is_onboarded BOOLEAN DEFAULT FALSE` to users table
- [x] Add `default_table_mode TEXT DEFAULT 'forced_audio'` to users table
- [x] Add `deleted_at TIMESTAMPTZ` and `deletion_scheduled_at TIMESTAMPTZ` (soft delete)
- [x] Backfill: `SET is_onboarded = TRUE WHERE pixel_avatar_id IS NOT NULL`

**Backend — Models & Endpoints:**
- [x] Update `UserProfile` model: add `is_onboarded`, `default_table_mode`, `deleted_at`, `deletion_scheduled_at`
- [x] Update `UserProfileUpdate` model: add `is_onboarded`, `default_table_mode` with validator
- [x] Add `DeleteAccountResponse` model
- [x] Add `soft_delete_user()` method to `UserService`
- [x] Add `DELETE /api/v1/users/me` endpoint (soft delete with 30-day grace)
- [x] Backend tests for soft delete, onboarding flag, updated fixtures

**Frontend — Onboarding Wizard (3 Screens):**
- [x] Refactor `/onboarding/page.tsx` into step-based wizard with progress indicator
- [x] Screen 1 — Welcome: CharacterSprite animations on styled gradient, "Your cozy corner for getting things done."
- [x] Screen 2 — Profile: username + display name + character picker (reuse `CharacterPicker`)
- [x] Screen 3 — House Rules: Stay Focused, Be Kind, Stay Accountable + "I'm in" CTA
- [x] Single `PATCH /users/me` on completion (username + display_name + pixel_avatar_id + is_onboarded=true)
- [x] Smooth step transitions + back buttons
- [x] Guard: already-onboarded users redirected to `/dashboard`

**Frontend — Onboarding Gate:**
- [x] Add `is_onboarded` check in `AuthProvider` after profile fetch
- [x] Redirect un-onboarded users to `/onboarding` via `window.location.href`
- [x] Prevent redirect loop (`/onboarding` is in `(auth)/` group, outside gate)

**Frontend — User Store Updates:**
- [x] Add missing fields to `UserProfile` interface: `pixel_avatar_id`, `is_onboarded`, `default_table_mode`, `longest_streak`, `last_session_date`, notification settings, `banned_until`, `deleted_at`

**Frontend — Profile Page (`/profile`):**
- [x] Identity section: large animated avatar, change character dialog, edit username + display name + bio
- [x] Stats section: total sessions, focus minutes, current streak, reliability badge (read from cached user fields)
- [x] Preferences section: default table mode toggle, ambient mix note, notification toggles
- [x] Account section: connected Google account, sign out, delete account (soft delete with confirmation)
- [x] Add "Profile" link to sidebar navigation

**Frontend Tests:**
- [x] Onboarding wizard: step navigation, validation, API call on completion
- [x] Profile page: renders sections, edit flow, save, delete account flow
- [x] Onboarding gate: redirects un-onboarded users, allows onboarded through

### Phase 3E: Utility & Polish
> **Design Doc:** [output/plan/2026-02-09-utility-polish-design.md](output/plan/2026-02-09-utility-polish-design.md)

- [x] Pixel-styled UI component variants
  - [x] Add pixel utility classes to globals.css (@utility shadow-pixel, border-pixel, rounded-pixel, font-pixel)
  - [x] Restyle HudOverlay: opaque bg, sharp corners, pixel font for timer + phase label
  - [x] Restyle ChatPanel: opaque bg, hard border, sharp corners, pixel font for header
  - [x] Add isPixelMode prop to ControlBar + AmbientMixerControls + PiPToggleButton
  - [x] Pass isPixelMode from PixelSessionLayout; verify classic mode unchanged
- [x] Room ambient animations (CSS keyframes, always on in pixel mode)
  - [x] Create RoomAmbientAnimation component (switch on roomType)
  - [x] Cozy Study: warm flickering lamp glow (radial gradient, 2s cycle)
  - [x] Coffee Shop: 3 rising steam wisps (staggered, 3-4s loops)
  - [x] Library: rain streaks on window (repeating gradient, 4s loop, ~12% opacity)
  - [x] Wire into PixelRoom between background (z-0) and characters (z-10)
- [x] 5-State character animation system (Working, Speaking, Away, Typing, Ghosting)
  - [x] Add isTyping tracking to usePresenceDetection (keyboard activity, 3s timeout)
  - [x] Extract getCharacterState() utility with priority logic + tests
  - [x] Expand SpriteState type, CharacterConfig states, all 8 character configs
  - [x] Wire isTyping through LiveKit data channel broadcast + participant objects
  - [x] Generate typing + ghosting sprite rows for 8 characters (Pillow script, 256x192 → 256x320)
  - [x] Tests: state priority (8 cases), typing detection (7 cases), sprite states (4 cases), ambient animation (4 cases)

---

### Phase 4: Alpha-Ready (Gamification + Launch Essentials)

#### Backend Hardening
> **Design Doc:** [output/plan/2026-02-09-backend-hardening-design.md](output/plan/2026-02-09-backend-hardening-design.md)

**Step 1: Constants Consolidation**
- [x] Add `REFLECTION_MAX_LENGTH`, `REASON_TEXT_MAX_LENGTH`, `TOPIC_MAX_LENGTH`, `REFERRAL_CODE_MAX_LENGTH`, `MAX_RATINGS_PER_BATCH`, pagination defaults to `constants.py`
- [x] Remove duplicated class attrs from `session_service.py` (MAX_PARTICIPANTS, AI_COMPANION_NAMES, etc.)
- [x] Remove local `REFLECTION_MAX_LENGTH` from `reflection_service.py`
- [x] Update Pydantic models to use constants for `max_length` (reflection, rating, session, credit models)

**Step 2: Centralized Logging**
- [x] Create `core/logging_config.py` with `JSONFormatter` + `setup_logging()` (JSON in prod, human-readable in dev)
- [x] Wire `setup_logging()` into `main.py` lifespan
- [x] Replace `print()` with `logger` in `main.py`, `analytics_service.py`, `middleware.py`

**Step 3: Global Exception Handlers**
- [x] Create `core/exceptions.py` with `register_exception_handlers(app)` — 21 exception → HTTP mappings
- [x] Register in `main.py`, add catch-all 500 handler with logging
- [x] Remove try/except boilerplate from `credits.py`, `sessions.py`, `users.py`, `reflections.py`
- [x] Update router tests (assert domain errors instead of HTTPException)

**Step 4: Rate Limiting**
- [x] Add `slowapi>=0.1.9` to `requirements.txt`, `rate_limit_enabled` to config
- [x] Create `core/rate_limit.py` with auth-keyed limiter + Redis backend
- [x] Apply rate limit decorators: 5/min (quick-match), 10/min (gift, rate, cancel), 15/min (profile), 60/min (default)
- [x] Rename `request` body params to avoid slowapi `Request` conflict (e.g., `gift_request: GiftRequest`)
- [x] Write tests for rate limit key extraction and 429 handler

#### Zero Credits UX
- [x] Create `useCountdown` hook (`frontend/src/hooks/use-countdown.ts`) + tests
- [x] Add backend "Notify Me" endpoint (`POST /credits/notify-interest`) + migration
- [x] Build `UpgradeModal` component (tier comparison + countdown + referral + "Coming Soon" pricing)
- [x] Build `ZeroCreditCard` dashboard info card (countdown-focused, between ratings alert and stats)
- [x] Modify `CreditBadge` — zero-state tooltip with countdown + click opens modal
- [x] Wire up: dashboard (render card + handle 402), app shell (render modal), header (pass props)

#### Chat Safety & Moderation
> **Design Doc:** [.claude/plans/humble-munching-zebra.md](.claude/plans/humble-munching-zebra.md)

**Three-layer moderation: client blocklist (enhanced) + server-side flag logging + user reports (escalation)**

**Backend:**
- [x] Add moderation constants to `constants.py` (report limits, flag window, description max length)
- [x] Create `models/moderation.py` (ReportCategory enum, request/response models, exceptions)
- [x] Create `services/moderation_service.py` (flag logging, report submission, duplicate/self-report prevention)
- [x] Create `routers/moderation.py` (POST /flag, POST /reports, GET /reports/mine)
- [x] Wire router into `main.py` + register exception handlers in `exceptions.py`
- [x] Write TDD tests: 7 service tests + 7 router tests

**Frontend — Blocklist Enhancement:**
- [x] Restructure `blocklist.ts` with categorized patterns + `getMatchedCategory()` function
- [x] Update `board-input.tsx` to POST flagged messages to backend (fire-and-forget)

**Frontend — Report Modal:**
- [x] Build `ReportModal` component (5 categories, description textarea, submit flow)
- [x] Add three-dot menu to `ParticipantSeat` with "Report User" option (non-AI, non-self only)
- [x] Add "Report a concern" link on session end page (always visible, participant picker)
- [x] Thread `sessionId` through TableView → ParticipantSeat → BoardInput

**Frontend Tests:**
- [x] ReportModal tests (category selection, submission, toasts)
- [x] Blocklist tests (`getMatchedCategory()` categorization, backward compat)

#### Internationalization (i18n)
> **Design Doc:** [.claude/plans/zany-herding-horizon.md](.claude/plans/zany-herding-horizon.md)

**Infrastructure:**
- [x] Configure next-intl plugin in `next.config.ts`
- [x] Create `src/i18n/request.ts` locale resolver (cookie-based)
- [x] Wrap root layout with `NextIntlClientProvider`
- [x] Integrate locale cookie with AuthProvider

**Components:**
- [x] Build `LanguageToggle` component (segmented + dropdown variants)
- [x] Add language toggle to onboarding Welcome step
- [x] Add bilingual language hint (opposite-language) on Welcome step
- [x] Add language preference dropdown to Profile/Settings page

**Translations (full extraction — all pages):**
- [x] Create `messages/en.json` with all namespaced strings
- [x] Create `messages/zh-TW.json` with Taiwan Traditional Chinese translations
- [x] Extract strings: auth + onboarding pages
- [x] Extract strings: dashboard + navigation/sidebar
- [x] Extract strings: session board + timer + seat cards
- [x] Extract strings: chat + moderation/report components
- [x] Extract strings: diary + reflection components
- [x] Extract strings: credits + upgrade modal
- [x] Extract strings: rating/peer review components
- [x] Extract strings: profile + settings + collection
- [x] Extract strings: shared components (modals, badges, placeholders, errors)

**Verification:**
- [x] Build passes with no errors
- [x] Lint passes
- [x] All existing tests pass
- [x] No missing translation key warnings in console

#### Find Table — Dashboard Hero Section
> **Design Doc:** [output/plan/2026-02-11-find-table-dashboard-hero.md](output/plan/2026-02-11-find-table-dashboard-hero.md)

**Backend:**
- [x] Add `TimeSlotInfo`, `UpcomingSlotsResponse` models + update `QuickMatchRequest` with `target_slot_time`
- [x] Add service methods: `calculate_upcoming_slots`, `get_slot_queue_counts`, `get_slot_estimates`, `get_user_sessions_at_slots`
- [x] Add `GET /upcoming-slots` endpoint + modify quick-match for `target_slot_time`
- [x] Add estimate constants to `constants.py`

**Frontend:**
- [x] Build `ModeToggle`, `TimeSlotCard`, `FindTableHero` components
- [x] Refactor dashboard: replace Quick Actions with `FindTableHero`
- [x] Remove "Find Table" from sidebar nav items
- [x] Add `findTable` i18n namespace (EN + zh-TW)

**Testing:**
- [x] Backend tests: upcoming-slots endpoint, service methods, target_slot_time validation
- [x] Frontend tests: FindTableHero, TimeSlotCard, ModeToggle components
- [x] Verification: all tests pass (491 backend, 354 frontend), lint clean, build succeeds

#### Accountability Partners & Private Study Groups
> **Design Doc:** [output/plan/2026-02-12-accountability-partners-design.md](output/plan/2026-02-12-accountability-partners-design.md)
> **Plan File:** [.claude/plans/stateful-popping-giraffe.md](.claude/plans/stateful-popping-giraffe.md)

**Database & Constants (Chunk 1):**
- [x] Migration `019_interest_tags.sql`: `user_interest_tags` table + RLS
- [x] Migration `020_partnerships.sql`: `partnerships` table + indexes + RLS
- [x] Migration `021_table_invitations.sql`: `table_invitations` table + indexes
- [x] Migration `022_recurring_schedules.sql`: `recurring_schedules` table + constraints
- [x] Migration `023_sessions_private_columns.sql`: add `is_private`, `created_by`, `recurring_schedule_id`, `max_seats` to sessions
- [x] Add interest tags, partnership, and schedule constants to `constants.py`

**Backend Models & Exceptions (Chunk 2):**
- [x] Create `models/partner.py`: enums, request/response models, domain exceptions
- [x] Create `models/schedule.py`: recurring schedule models
- [x] Register new exception handlers in `core/exceptions.py`

**Backend Services (Chunk 3):**
- [x] Create `PartnerService` (`services/partner_service.py`): request flow, list, remove, search, interest tags, last-session tracking
- [x] Create `ScheduleService` (`services/schedule_service.py`): CRUD, auto-session creation logic
- [x] Modify `SessionService`: add `is_private` filter to `find_matching_session()`, private session creation, invitation handling
- [x] Post-session integration: update `last_session_together` for partner pairs

**Backend Routers & Tasks (Chunk 4):**
- [x] Create `routers/partners.py`: 6 endpoints (list, requests, search, send, respond, remove)
- [x] Create `routers/schedules.py`: 4 endpoints (list, create, update, delete)
- [x] Modify `routers/sessions.py`: add create-private, invitations, invite-respond endpoints
- [x] Modify `routers/users.py`: add interest tags endpoint, partnership status in public profile
- [x] Create `tasks/schedule_tasks.py`: hourly Celery task for auto-session creation
- [x] Register new routers in `main.py`

**Backend Tests (Chunk 5 — TDD):**
- [x] `test_partner_service.py` (25 tests): send, respond, list, remove, tags, search, partnership status
- [x] `test_schedule_service.py` (25 tests): create, permissions, auto-creation, timezone, update, delete
- [x] `test_partners.py` (23 tests) + `test_schedules.py` (18 tests) router tests
- [x] All existing tests still pass — 582 total (91 new, 491 pre-existing)

**Frontend Store & Components (Chunk 6):**
- [x] Create `stores/partner-store.ts`: Zustand store for partner state + API calls
- [x] Build `PartnerCard` component (avatar, name, tags, last session, actions)
- [x] Build `PartnerRequestCard` component (accept/decline/cancel)
- [x] Build `CreatePrivateTableModal` (multi-step: slot → partners → config → confirm)
- [x] Build `InvitationAlert` dashboard card
- [x] Build `AddPartnerButton` (reusable, state-aware)
- [x] Build `InterestTagPicker` + `InterestTagBadge` components
- [x] Add `partners`, `schedule` i18n namespaces (EN + zh-TW)

**Frontend Pages & Modifications (Chunk 7):**
- [x] Create `/partners` page (card grid, tabs: Partners/Requests/Invitations, search)
- [x] Create `/partners/schedules` page (Coming Soon placeholder, unlimited-gated)
- [x] Add "Partners" to sidebar navigation (Users2 icon)
- [x] Dashboard: add invitation alerts
- [x] Session end page: add "Add as Partner" button per human tablemate
- [x] Profile page: add interest tags section

#### Partner Direct Messaging (Chat) — Deferred
- [ ] Design chat system architecture (real-time vs async)
- [ ] Build partner chat UI
- [ ] Implement message persistence
- [ ] Add chat notifications


#### Gamification
- [x] Award essence on session completion (implemented in webhook room_finished handler)
- [ ] Implement `EssenceService` for furniture essence (purchase, spend, history)
- [ ] Implement streak bonuses (10 sessions = bonus essence)
- [ ] Build item catalog display (pixel art collectibles)
- [ ] Add item purchase flow
- [ ] More room types as collectible/unlockable rewards
- [ ] Character customization (accessories, color swaps, cosmetics via essence)

---

## Phase 5: Launch Prep

### Notifications
- [ ] Set up email service (Resend/SendGrid)
- [ ] Implement browser push notifications
- [ ] Create notification preferences settings
- [ ] Send notifications for: session start, match found, credit refresh, Red rating


### Analytics (Basic)
- [ ] Integrate PostHog
- [ ] Instrument key events (session_start, session_complete, rating_submitted, etc.)
- [ ] Add user identification and properties

### Payment Integration
- [ ] Research Taiwan payment gateways (ECPay, LINE Pay, NewebPay) or international (Stripe, LemonSqueezy)
- [ ] Document integration requirements
- [ ] Design subscription upgrade flow (UI mockups)
- [ ] Implement payment processing

### Production Hardening
- [ ] Security audit (OWASP top 10, use [shannon](https://github.com/KeygraphHQ/shannon))
- [ ] Add JWKS cache TTL (1-hour expiration with background refresh)
- [ ] Convert JWKS fetch to async (`httpx.AsyncClient`)
- [ ] Performance testing
- [ ] Mobile responsiveness check
- [ ] Accessibility audit (basic)

### PWA
- [ ] Service worker for offline shell
- [ ] Web app manifest for installation
- [ ] Push notification support (Web Push API)

### Admin Tools & Operations
- [ ] Create admin moderation queue (basic)
- [ ] Admin dashboard for user management
- [ ] Set up operation tools, such as add/deduct credits, etc. Need to brainstorm a bit more (this is for the operation team)

### Legal & Compliance
- [ ] Legal audit (any legality issues?)
- [ ] Taiwan PDPA compliance review
- [ ] End-to-end flow testing

### Marketing
- [ ] Landing page (need to be SEO-friendly)
- [ ] Content marketing (for SEO)
  - [ ] "Body doubling" research as marketing assets, or some built in prompts in the system
  - [ ] Comments about attention span issues, how to regain focus, etc.

---

## Appendix: Post-Launch Improvement Ideas

### Customizable Avatar Builder
- Replace CharacterPicker with mix-and-match avatar builder
- Components: 10+ hair styles, 5+ face shapes, accessories, colors/tints
- Canvas-based compositing engine for layer rendering
- Store as `avatar_config` JSON (field already exists in DB)
- Estimated effort: 3-5 days depending on art asset sourcing