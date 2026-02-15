# PostHog Analytics Integration — Design Document

**Date**: 2026-02-15
**Status**: Approved

## Summary

Integrate PostHog as the single analytics platform for Focus Squad, replacing the existing custom analytics system. Client-side + server-side hybrid approach with autocapture for UI interactions and manual instrumentation for ~52 business events.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Analytics platform | PostHog (Cloud, free tier) | Robust ecosystem, generous free tier, product analytics + funnels |
| Approach | Client + Server hybrid | Full coverage — frontend UI events + backend business logic events |
| Person ID | `user_id` (internal DB UUID) | Primary key everywhere, aligns with all DB tables |
| Naming convention | `noun_verb` snake_case | Feature-grouped (all `rating_*` together), verb at end indicates type |
| Capture strategy | Autocapture + manual business events | Autocapture for broad UI coverage, manual for rich business context |
| Consent model | Opt-out by default | Respect existing `activity_tracking_enabled` toggle, Taiwan market |
| Session groups | PostHog Groups (`session_id`) | Per-table analytics (completion rate, engagement per session) |
| Cross-source analysis | Phase 1: Rich person properties. Phase 2: Export to Supabase | Person properties cover 90% of needs. Export adds full SQL JOIN power later |
| Existing analytics | Remove entirely | PostHog becomes single source of truth. Less code to maintain |

## 1. Identity & Consent

### Identity Flow

```
Anonymous visit → PostHog generates $distinct_id (random UUID)
                  ↓
User logs in    → posthog.identify(user_id, { email, username, tier, ... })
                  ↓
PostHog merges  → anonymous events + identified events = one Person
                  ↓
Backend events  → posthog.capture(distinct_id=user_id, event=...)
                  (same user_id, so events automatically link)
```

### Person Properties (synced from Supabase)

Set on `identify()` and updated when values change:

- `email`, `username`, `display_name`
- `tier` (free/pro/elite/infinite)
- `is_paid` (boolean)
- `reliability_score`
- `total_sessions`, `weekly_streak`
- `onboarded` (boolean), `onboarded_at`
- `created_at`
- `preferred_mode` (forced_audio/quiet)
- `locale` (en/zh-TW)

### Session Groups

Each session is a PostHog Group with key `session` and ID `session_id`:

```typescript
posthog.group('session', sessionId, {
  mode: 'forced_audio',
  participant_count: 4,
  start_time: '2026-02-15T10:00:00Z'
});
```

### Consent

- Track by default (opt-out model)
- `activity_tracking_enabled === false` → `posthog.opt_out_capturing()`
- Toggled back on → `posthog.opt_in_capturing()`
- Backend: check user preference before `capture()` calls

## 2. Event Taxonomy (52 Events)

### Naming Convention

`noun_verb` snake_case — feature-grouped, verb at end indicates event type:

| Verb suffix | Meaning | Example |
|-------------|---------|---------|
| `_viewed` | User saw something (impression) | `rating_prompt_viewed` |
| `_clicked` | User tapped/clicked a CTA | `find_table_clicked` |
| `_submitted` | User completed a form/input | `rating_submitted` |
| `_started` | User began a flow | `onboarding_started` |
| `_completed` | User/system finished a flow | `session_completed` |
| `_toggled` | User flipped a setting | `mic_toggled` |
| `_changed` | State transition | `session_phase_changed` |
| Server-only events | Backend-triggered, no direct user action | `credits_refreshed`, `user_banned` |

### Auth & Onboarding

| Event | Source | Key Properties |
|-------|--------|---------------|
| `auth_signed_up` | Server | `auth_provider`, `locale` |
| `auth_logged_in` | Client | `method` |
| `auth_logged_out` | Client | — |
| `onboarding_started` | Client | — |
| `onboarding_step_viewed` | Client | `step`, `step_name` |
| `onboarding_step_completed` | Client | `step`, `step_name`, `selection` |
| `onboarding_completed` | Server | `time_to_complete_seconds` |

### Session Matching Funnel

| Event | Source | Key Properties |
|-------|--------|---------------|
| `find_table_clicked` | Client | `mode` |
| `session_match_succeeded` | Server | `session_id`, `mode`, `wait_minutes`, `participant_count` |
| `session_match_failed` | Server | `mode`, `reason` |
| `waiting_room_entered` | Client | `session_id`, `wait_minutes` |
| `waiting_room_abandoned` | Client | `session_id`, `waited_seconds`, `remaining_seconds` |

### Session Lifecycle (Group: session_id)

| Event | Source | Key Properties |
|-------|--------|---------------|
| `session_joined` | Server | `session_id`, `mode`, `participant_count` |
| `session_phase_changed` | Server | `session_id`, `from_phase`, `to_phase` |
| `session_left_early` | Server | `session_id`, `phase_at_exit`, `minutes_completed` |
| `session_completed` | Server | `session_id`, `total_minutes`, `earned_essence` |
| `mic_toggled` | Client | `session_id`, `phase`, `enabled` |
| `board_message_sent` | Client | `session_id`, `phase` |
| `audio_connected` | Client | `session_id` |
| `audio_disconnected` | Client | `session_id`, `reason` |

### Focus & App Lifecycle

| Event | Source | Key Properties |
|-------|--------|---------------|
| `app_opened` | Client | `referrer` |
| `tab_focus_changed` | Client | `session_id` (if in session), `visible` (bool) |
| `error_page_viewed` | Client | `error_type`, `path` |

### Rating & Trust

| Event | Source | Key Properties |
|-------|--------|---------------|
| `rating_prompt_viewed` | Client | `session_id`, `pending_count` |
| `rating_prompt_dismissed` | Client | `session_id` |
| `rating_submitted` | Server | `session_id`, `rating` (green/red/skip) |
| `user_banned` | Server | `ban_reason`, `ban_duration_hours` |
| `ban_page_viewed` | Client | `ban_remaining_hours` |

### Credits & Economy

| Event | Source | Key Properties |
|-------|--------|---------------|
| `credit_used` | Server | `session_id`, `credits_remaining`, `tier` |
| `credits_refreshed` | Server | `tier`, `new_balance` |
| `zero_credits_viewed` | Client | `tier`, `next_refresh_date` |
| `upgrade_prompt_viewed` | Client | `current_tier`, `context` |
| `upgrade_clicked` | Client | `current_tier`, `target_tier` |

### Diary & Reflections

| Event | Source | Key Properties |
|-------|--------|---------------|
| `diary_viewed` | Client | — |
| `diary_entry_viewed` | Client | `session_id` |
| `reflection_submitted` | Client | `session_id`, `has_notes` |

### Room & Gamification

| Event | Source | Key Properties |
|-------|--------|---------------|
| `room_viewed` | Client | `is_own_room` |
| `room_visit_viewed` | Client | `visited_user_id` |
| `room_decorated` | Client | `item_type` |
| `shop_viewed` | Client | — |
| `shop_item_clicked` | Client | `item_id`, `item_type`, `price` |
| `shop_purchase_completed` | Client | `item_id`, `item_type`, `price` |
| `timeline_viewed` | Client | — |
| `streak_achieved` | Server | `streak_count` |
| `essence_earned` | Server | `session_id`, `amount` |

### Partners & Social

| Event | Source | Key Properties |
|-------|--------|---------------|
| `partner_list_viewed` | Client | — |
| `partner_invite_clicked` | Client | — |
| `partner_invite_accepted` | Server | `partnership_id` |
| `partner_schedule_viewed` | Client | — |

### Settings & Profile

| Event | Source | Key Properties |
|-------|--------|---------------|
| `profile_viewed` | Client | — |
| `profile_updated` | Client | `fields_changed` |
| `language_switched` | Client | `from_locale`, `to_locale` |
| `activity_tracking_toggled` | Client | `enabled` |

## 3. Integration Architecture

### Frontend

```
frontend/src/
├── lib/
│   └── posthog/
│       ├── client.ts          # PostHog init + config
│       ├── identify.ts        # identify() + person properties
│       └── events.ts          # Type-safe capture helpers
├── components/
│   └── providers/
│       └── PostHogProvider.tsx # React provider (wraps app)
└── app/
    └── (protected)/
        └── layout.tsx         # identify() on auth
```

- `PostHogProvider.tsx`: Wraps root layout, initializes PostHog with public API key, enables autocapture
- `client.ts`: Singleton instance, handles opt-out/opt-in, manual `$pageview` for SPA route changes
- `identify.ts`: Called after login, sets `distinct_id` = `user_id`, sets person properties and session group
- `events.ts`: Type-safe wrappers preventing event name typos with autocomplete

### Backend

```
backend/app/
├── core/
│   └── posthog.py             # PostHog client singleton + capture helper
└── services/
    └── (existing services)    # capture() calls alongside business logic
```

- `posthog.py`: Initializes `posthog-python`, provides `capture()` helper that checks consent and auto-attaches session group
- Service integration: Events fire as side effects in existing services (no new endpoints)

### Remove Old Analytics

- Delete `backend/app/routers/analytics.py`
- Delete `backend/app/services/analytics_service.py`
- Remove frontend `POST /analytics/track` calls
- Keep `session_analytics_events` table (stop writing, keep historical data)

### Environment Variables

```bash
# Frontend
NEXT_PUBLIC_POSTHOG_KEY=phc_...
NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com

# Backend
POSTHOG_API_KEY=phx_...
POSTHOG_HOST=https://us.i.posthog.com
```

### Data Flow

```
┌─────────────────────────────────────────────────────┐
│  Frontend (Next.js)                                 │
│  PostHogProvider (root layout)                      │
│    ├── autocapture: pageviews, clicks, inputs       │
│    ├── identify(user_id, person_props)              │
│    ├── group('session', session_id, session_props)  │
│    └── capture('event_name', { ...props })          │
└────────────────────┬────────────────────────────────┘
                     │ HTTPS → PostHog Cloud
                     ▼
              ┌─────────────┐
              │  PostHog     │  ← Merges client + server by user_id
              │  Cloud       │  ← Session groups link per-table events
              └─────────────┘
                     ▲
                     │ HTTPS → PostHog Cloud
┌────────────────────┴────────────────────────────────┐
│  Backend (FastAPI)                                  │
│  posthog.capture(user_id, 'event', { ...props })    │
│    ├── credit_service → credit_used, refreshed      │
│    ├── session_service → joined, phase_changed      │
│    ├── rating_service → rating_submitted, banned    │
│    └── user_service → signed_up, onboarding_done   │
└─────────────────────────────────────────────────────┘
```

## 4. Cross-Source Analysis Strategy

### Phase 1 (This Implementation): Rich Person Properties

Sync key Supabase fields as PostHog person properties so you can segment any PostHog report by business data:

- `tier`, `is_paid`, `reliability_score`, `total_sessions`, `weekly_streak`
- `created_at`, `onboarded_at`, `preferred_mode`, `locale`

Updated server-side whenever values change via `posthog.capture('$set', ...)`.

### Phase 2 (Future): Export PostHog Events to Supabase

- Create `posthog_events` table in Supabase
- PostHog webhook sends events to a backend ingestion endpoint
- Full SQL JOIN power across behavioral + business data
- One-time backfill of historical events via PostHog Events API (1 year retention on free tier)

## 5. PostHog Dashboards & Funnels (Post-Setup)

### Core Funnels

1. **Signup → First Session**: `auth_signed_up → onboarding_completed → find_table_clicked → session_joined → session_completed`
2. **Return Session**: `session_completed (1st) → app_opened (7 days) → find_table_clicked → session_completed (2nd)`
3. **Matching → Completion**: `find_table_clicked → session_match_succeeded → waiting_room_entered → session_joined → session_completed`
4. **Rating Compliance**: `rating_prompt_viewed → rating_submitted vs rating_prompt_dismissed`

### Key Dashboards

1. Daily/Weekly Active Users
2. Session Health (completion rate, early leaves by phase)
3. Onboarding conversion (step-by-step)
4. Economy (credit usage, zero-credit frequency, upgrade funnel)
5. Focus Quality (`tab_focus_changed` during work phases)

### Cohort Definitions

- Power Users: 3+ sessions/week
- At Risk: No session in 7+ days after first session
- New Users: Signed up in last 7 days
- Paid Users: `tier != 'free'`
