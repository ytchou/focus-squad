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
- [ ] Configure NextAuth with Google OAuth provider
- [ ] Create auth middleware for protected routes
- [ ] Build login page with Google OAuth button
- [ ] Build onboarding flow (username selection)
- [ ] Set up Supabase client (SSR-compatible)

### Frontend Foundation
- [ ] Implement design system (earth tones, warm accents)
- [ ] Create base layout component
- [ ] Set up Zustand stores (user, ui)
- [ ] Create reusable UI components (Button, Card, Avatar, etc.)
- [ ] Configure Tailwind with custom color palette

### Testing Foundation
- [ ] Set up pytest with async support (backend)
- [ ] Write tests for auth middleware
- [ ] Set up Jest/Vitest for frontend
- [ ] Add CI workflow for running tests

---

## Phase 2: Core Loop (Week 3-4)

### Session System (Backend)
- [ ] Implement `SessionService` for table management
- [ ] Complete `POST /api/v1/sessions/quick-match` (matching algorithm)
- [ ] Complete `GET /api/v1/sessions/upcoming` (time slot listing)
- [ ] Complete `GET /api/v1/sessions/{session_id}` (session details)
- [ ] Complete `POST /api/v1/sessions/{session_id}/leave` (early exit)
- [ ] Implement session state machine (Setup → Work_1 → Break → Work_2 → Social → Ended)
- [ ] Add AI companion seat filling logic

### LiveKit Integration
- [ ] Implement LiveKit token generation endpoint
- [ ] Create LiveKit room management service
- [ ] Handle participant join/leave events
- [ ] Implement audio-only room configuration
- [ ] Add Quiet Mode (muted by default) support

### Credit System (Backend)
- [ ] Implement `CreditService` for credit operations
- [ ] Complete `GET /api/v1/credits/balance` endpoint
- [ ] Complete `POST /api/v1/credits/gift` endpoint
- [ ] Complete `GET /api/v1/credits/referral` endpoint
- [ ] Complete `POST /api/v1/credits/referral/apply` endpoint
- [ ] Implement weekly credit refresh (cron job or trigger)
- [ ] Add credit transaction logging

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
