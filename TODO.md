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

- [ ] Source royalty-free pixel art assets from itch.io/OpenGameArt
  - 3 room backgrounds: cozy study room, coffee shop, library (isometric, 4 desk positions each)
  - 8+ character sprite sheets: distinct styles, 3 states (working/speaking/away), 3-4 frames each
  - Color-adjust assets to match design tokens (earth tones)
- [ ] Create asset pipeline and room config (`frontend/src/config/pixel-rooms.ts`)
- [ ] Database migration `013_pixel_art_system.sql`: `pixel_avatar_id` on users, `room_type` on sessions
- [ ] Backend updates: models, services, constants for pixel avatar + room type
- [ ] Add pixel design tokens to `globals.css` (`--font-pixel`, `--border-pixel`, `--shadow-pixel`)
- [ ] Build `CharacterSprite` component with CSS sprite animation (steps() timing)
  - 3 states: working (4fps), speaking (6fps, 2s debounce), away (3fps)
- [ ] Build `CharacterLayer` component (maps participants to sprites at desk positions)
- [ ] Build `PixelRoom` background component (full viewport, object-fit cover)
- [ ] Build `HudOverlay` (semi-transparent top bar: timer, phase, credits, leave)
- [ ] Build `ChatPanel` (floating right panel, expands during reflection phases)
- [ ] Create `PixelSessionLayout` (full-scene: room + characters + HUD + chat + controls)
- [ ] Extract current layout to `ClassicSessionLayout` (preserved as fallback toggle)
- [ ] Integrate pixel/classic toggle in session page (default: pixel, stored in localStorage)
- [ ] Build `CharacterPicker` component (grid of 8+ animated previews)
- [ ] Add character selection to onboarding flow
- [ ] Tests: CharacterSprite, pixel-rooms config, CharacterPicker

### Phase 3B: Immersion Layer

- [ ] Ambient Sound Mixer
  - [ ] Source royalty-free audio tracks
    - Lo-Fi Beats: [Pixabay](https://pixabay.com/music/search/lofi/) (no attribution required)
    - Coffee Shop Chatter: [Mixkit](https://mixkit.co/free-sound-effects/ambience/) (no attribution required)
    - Rain: [Mixkit](https://mixkit.co/free-sound-effects/rain/) (no attribution required)
  - [ ] Trim audio files to seamless loops (~2-5 min each)
  - [ ] Build `useAmbientMixer` hook with WebAudioAPI
    - AudioBufferSourceNode → GainNode → AudioContext.destination per track
    - Independent on/off and volume control per track
    - Mixable (multiple tracks simultaneously)
    - Local-only playback (never sent to LiveKit)
  - [ ] Add ambient mixer controls to session bottom bar (3 toggle buttons)
  - [ ] Persist ambient preferences to localStorage per user
- [ ] Full Character Animation States (8 states)
  - [ ] Add typing, sound-reaction, flow-state, ghosting, phase-transition states
  - [ ] Connect to activity detection signals
- [ ] Activity & Presence Detection
  - [ ] Implement Page Visibility API integration (`document.visibilityState` + `visibilitychange` event)
  - [ ] Implement local audio level detection via WebAudioAPI
    - Fork mic MediaStream: LiveKit path + local AnalyserNode path
    - `getByteFrequencyData()` → compute RMS volume level
    - 3-second baseline calibration on session start
    - Works even when mic muted in LiveKit (Quiet Mode presence detection)
  - [ ] Build activity state machine with grace periods
    - ACTIVE: page visible OR audio above threshold
    - Grace: <2 min since last signal → stay ACTIVE
    - AWAY: 2-5 min since last signal ("in flow")
    - GHOSTING: >5 min since last signal
  - [ ] Broadcast activity state via LiveKit data channel to other participants
  - [ ] Connect activity state to character sprite animations
  - [ ] Replace current `useActivityTracking` hook (keyboard/mouse based) with new signal-based system

### Phase 3C: Utility & Polish

- [ ] Picture-in-Picture (PiP) mini view
  - Canvas-rendered: timer + 4 avatar sprites with status borders
  - PiP active = page considered "visible" for activity
- [ ] Pixel-styled UI component variants (HUD bar, chat panel, control bar refinement)
- [ ] Room ambient animations (flickering lamp, coffee steam, rain on window)

### Avatar & Profile
- [ ] Build user profile page with pixel art avatar display
- [ ] Display session statistics and streaks
- [ ] Show reliability badge and rating history

### Gamification
- [x] Award essence on session completion (implemented in webhook room_finished handler)
- [ ] Implement `EssenceService` for furniture essence (purchase, spend, history)
- [ ] Implement streak bonuses (10 sessions = bonus essence)
- [ ] Build item catalog display (pixel art collectibles)
- [ ] Add item purchase flow
- [ ] More room types as collectible/unlockable rewards
- [ ] Character customization (accessories, color swaps, cosmetics via essence)

---

## Phase 4: Launch Prep (Week 7-8)

### Internationalization (i18n)
- [ ] Configure next-intl with EN + zh-TW
- [ ] Create translation files for all UI strings
- [ ] Add language switcher component
- [ ] Translate all static content

### Notifications
- [ ] Set up email service (Resend/SendGrid)
- [ ] Implement browser push notifications
- [ ] Create notification preferences settings
- [ ] Send notifications for: session start, match found, credit refresh, Red rating

### Analytics
- [ ] Integrate Mixpanel/Amplitude
- [ ] Instrument key events (session_start, session_complete, rating_submitted, etc.)
- [ ] Add user identification and properties

### Moderation
- [ ] Build report submission flow
- [ ] Create admin moderation queue (basic)

### Payment Research
- [ ] Research Taiwan payment gateways (ECPay, LINE Pay, NewebPay)
- [ ] Document integration requirements
- [ ] Design subscription upgrade flow (UI mockups)

### Pre-Launch Checklist
- [ ] Security audit (OWASP top 10)
- [ ] Performance testing
- [ ] Mobile responsiveness check
- [ ] Accessibility audit (basic)
- [ ] Error handling and user-friendly messages
- [ ] Add rate limiting middleware (`slowapi`)
- [ ] Implement structured logging (replace `print()` with `structlog`)
- [ ] Add JWKS cache TTL (1-hour expiration with background refresh)
- [ ] Convert JWKS fetch to async (`httpx.AsyncClient`)