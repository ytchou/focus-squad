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
- [ ] Create LiveKit room management service (room creation/deletion)
  - [ ] Add `constants.py` with timing values (grace period, room lead time, etc.)
  - [ ] Create `LiveKitService` with `create_room()`, `delete_room()`, `get_room()`, `generate_token()`
  - [ ] Mode-aware token generation (Forced Audio: canPublish=true, Quiet Mode: canPublish=false)
- [ ] Setup Celery for scheduled tasks
  - [ ] Add `celery[redis]` to requirements.txt
  - [ ] Create `celery_app.py` configuration
  - [ ] Create `tasks/livekit_tasks.py` (room creation at T-30s, cleanup after session)
- [ ] Handle participant join/leave events (webhooks)
  - [ ] Create `routers/webhooks.py` with `POST /api/v1/webhooks/livekit`
  - [ ] Validate webhook signature with `WebhookReceiver`
  - [ ] Handle events: participant_joined, participant_left, track_published, room_finished
  - [ ] Update participant connection status in database
- [ ] Implement audio-only room configuration
- [ ] Add Quiet Mode (muted by default) support
- [ ] Add migration for session_participants columns (connected_at, disconnected_at, is_connected)
- [ ] Integrate Celery tasks with quick-match endpoint

### Credit System (Backend)
- [x] Implement `CreditService` (minimal - balance, deduct, add)
- [x] Add credit transaction logging (in CreditService)
- [ ] Complete `GET /api/v1/credits/balance` endpoint
- [ ] Complete `POST /api/v1/credits/gift` endpoint
- [ ] Complete `GET /api/v1/credits/referral` endpoint
- [ ] Complete `POST /api/v1/credits/referral/apply` endpoint
- [ ] Implement weekly credit refresh (cron job or trigger)

### Session UI (Frontend)
- [ ] Build dashboard/home page (upcoming sessions, stats)
- [ ] Create session lobby page (waiting for match)
- [ ] Build study session page with 55-min timer
- [ ] Implement LiveKit audio integration (mute/unmute)
- [ ] Add active status indicators (waveform, typing)
- [ ] Create session end screen

### Timer & State Sync
- [ ] Implement shared Pomodoro timer (via LiveKit data channel)
- [ ] Sync session phase transitions across participants
- [ ] Handle disconnect/reconnect grace period (2 min)

---

## Phase 3: Social & Polish (Week 5-6)

### Peer Review System (Backend)
- [ ] Implement `RatingService` for peer reviews
- [ ] Complete `POST /api/v1/sessions/{session_id}/rate` endpoint
- [ ] Calculate reliability score (weighted average with time decay)
- [ ] Implement 3-Red penalty system (48hr ban + credit loss)
- [ ] Add high-reliability voter weight bonus

### Peer Review UI (Frontend)
- [ ] Build peer review modal (Green/Red/Skip)
- [ ] Show reliability badge on user profiles
- [ ] Display rating history in user dashboard

### Chat System
- [ ] Implement chat message storage and retrieval
- [ ] Add keyword filtering for inappropriate content
- [ ] Build in-session text chat UI
- [ ] Add content flagging for moderation

### Avatar & Profile
- [ ] Create avatar builder component
- [ ] Implement avatar customization options (hair, face, accessories)
- [ ] Build user profile page
- [ ] Display collection grid (furniture items)
- [ ] Show session statistics and streaks

### Gamification
- [ ] Implement `EssenceService` for furniture essence
- [ ] Award essence on 47-min core completion
- [ ] Implement streak bonuses (10 sessions = bonus)
- [ ] Build item catalog display
- [ ] Add item purchase flow

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
- [ ] Create analytics dashboard queries

### Moderation
- [ ] Build report submission flow
- [ ] Create admin moderation queue (basic)
- [ ] Implement report review actions

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
- [ ] Documentation (API docs, setup guide)
- [ ] Add rate limiting middleware (`slowapi`)
- [ ] Implement structured logging (replace `print()` with `structlog`)
- [ ] Add JWKS cache TTL (1-hour expiration with background refresh)
- [ ] Convert JWKS fetch to async (`httpx.AsyncClient`)

---

## Discovered Tasks
> Add new tasks here as they're discovered during development

(No unplaced tasks - all items from Backend Infrastructure review have been sorted into appropriate sections)

---

## Completed Archive
> Move completed sections here to keep the active list clean
