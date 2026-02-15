# PostHog Analytics Integration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Integrate PostHog as the single analytics platform with client+server hybrid, replacing the existing custom analytics system.

**Architecture:** `posthog-js` in the Next.js frontend (autocapture + manual events) and `posthog-python` in the FastAPI backend (business logic events). Single PostHog project, `user_id` as distinct_id, session Groups for per-table analytics. Old analytics router/service removed.

**Tech Stack:** PostHog Cloud (free tier), `posthog-js` ^1.x, `posthog-python` ^3.x

**Design Doc:** `docs/plans/2026-02-15-posthog-analytics-design.md`

---

## Task 1: Install PostHog dependencies

**Files:**
- Modify: `frontend/package.json`
- Modify: `backend/requirements.txt`
- Modify: `frontend/.env.example`
- Modify: `backend/.env.example` (if exists, otherwise `backend/app/core/config.py`)

**Step 1: Install frontend PostHog package**

```bash
cd frontend && npm install posthog-js
```

**Step 2: Add PostHog env vars to frontend .env.example**

Add to `frontend/.env.example`:
```
# PostHog Analytics
NEXT_PUBLIC_POSTHOG_KEY=
NEXT_PUBLIC_POSTHOG_HOST=https://us.i.posthog.com
```

**Step 3: Install backend PostHog package**

```bash
cd backend && source venv/bin/activate && pip install posthog>=3.0.0
```

Add to `backend/requirements.txt`:
```
posthog >= 3.0.0
```

**Step 4: Add PostHog config to backend Settings**

In `backend/app/core/config.py`, add to `Settings` class (after line 50, the `rate_limit_enabled` field):
```python
    # PostHog Analytics
    posthog_api_key: str = ""
    posthog_host: str = "https://us.i.posthog.com"
    posthog_enabled: bool = True
```

Do NOT add `posthog_api_key` to `REQUIRED_SECRETS` — analytics should not block app startup.

**Step 5: Commit**

```bash
git add -A && git commit -m "chore: install posthog-js and posthog-python dependencies"
```

---

## Task 2: Create frontend PostHog client + provider

**Files:**
- Create: `frontend/src/lib/posthog/client.ts`
- Create: `frontend/src/lib/posthog/identify.ts`
- Create: `frontend/src/components/providers/posthog-provider.tsx`
- Modify: `frontend/src/app/layout.tsx` (wrap children with provider)

**Step 1: Create PostHog client singleton**

Create `frontend/src/lib/posthog/client.ts`:
```typescript
import posthog from "posthog-js";

export const POSTHOG_KEY = process.env.NEXT_PUBLIC_POSTHOG_KEY ?? "";
export const POSTHOG_HOST = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://us.i.posthog.com";

let initialized = false;

export function initPostHog(): typeof posthog {
  if (typeof window === "undefined") return posthog;
  if (initialized) return posthog;
  if (!POSTHOG_KEY) {
    console.warn("[PostHog] No API key configured — analytics disabled");
    return posthog;
  }

  posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    capture_pageview: false, // We handle manually for SPA routing
    capture_pageleave: true,
    autocapture: true,
    persistence: "localStorage+cookie",
    loaded: (ph) => {
      if (process.env.NODE_ENV === "development") {
        console.log("[PostHog] Initialized in development mode");
      }
    },
  });

  initialized = true;
  return posthog;
}

export function getPostHog(): typeof posthog {
  return posthog;
}
```

**Step 2: Create identify helper**

Create `frontend/src/lib/posthog/identify.ts`:
```typescript
import posthog from "posthog-js";
import type { UserProfile } from "@/stores/user-store";

export function identifyUser(profile: UserProfile): void {
  if (!posthog.__loaded) return;

  posthog.identify(profile.id, {
    email: profile.email,
    username: profile.username,
    display_name: profile.display_name,
    tier: profile.credit_tier,
    is_paid: profile.credit_tier !== "free",
    reliability_score: profile.reliability_score,
    total_sessions: profile.session_count,
    weekly_streak: profile.current_streak,
    onboarded: profile.is_onboarded,
    preferred_mode: profile.default_table_mode,
    locale: profile.preferred_language,
    created_at: profile.created_at,
  });
}

export function resetUser(): void {
  if (!posthog.__loaded) return;
  posthog.reset();
}

export function setUserOptOut(optOut: boolean): void {
  if (!posthog.__loaded) return;
  if (optOut) {
    posthog.opt_out_capturing();
  } else {
    posthog.opt_in_capturing();
  }
}
```

**Step 3: Create PostHogProvider component**

Create `frontend/src/components/providers/posthog-provider.tsx`:
```typescript
"use client";

import { useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import posthog from "posthog-js";
import { initPostHog, POSTHOG_KEY } from "@/lib/posthog/client";

export function PostHogProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    initPostHog();
  }, []);

  // Track SPA pageviews on route change
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (!POSTHOG_KEY) return;
    if (!posthog.__loaded) return;

    const url = window.origin + pathname + (searchParams?.toString() ? `?${searchParams.toString()}` : "");
    posthog.capture("$pageview", { $current_url: url });
  }, [pathname, searchParams]);

  return <>{children}</>;
}
```

**Step 4: Wrap app in PostHogProvider**

Modify `frontend/src/app/layout.tsx`. The root layout is a server component, so we need to wrap inside the body. PostHogProvider must be inside `NextIntlClientProvider` (or alongside it) but outside protected routes so anonymous pageviews are captured too.

Change line 42 from:
```tsx
<NextIntlClientProvider messages={messages}>{children}</NextIntlClientProvider>
```
to:
```tsx
<NextIntlClientProvider messages={messages}>
  <PostHogProvider>{children}</PostHogProvider>
</NextIntlClientProvider>
```

Add import at top:
```typescript
import { PostHogProvider } from "@/components/providers/posthog-provider";
```

Note: `PostHogProvider` is a client component. Wrapping server-component children in a client component is fine in Next.js — children are passed as props and rendered on the server.

**Step 5: Commit**

```bash
git add -A && git commit -m "feat: add PostHog provider and client initialization"
```

---

## Task 3: Add identify() to auth flow + consent

**Files:**
- Modify: `frontend/src/components/providers/auth-provider.tsx`

**Step 1: Add PostHog identify on login**

In `frontend/src/components/providers/auth-provider.tsx`:

Add import at top:
```typescript
import { identifyUser, resetUser, setUserOptOut } from "@/lib/posthog/identify";
```

After line 65 (`useUserStore.getState().setUser(activeProfile);`), add:
```typescript
          // PostHog: identify user and set consent
          identifyUser(activeProfile);
          setUserOptOut(!activeProfile.activity_tracking_enabled);
```

After line 84 (`useUserStore.getState().clearUser();`), add:
```typescript
        resetUser();
```

Also, for the onboarding case (un-onboarded users, around line 39 after `useUserStore.getState().setUser(profile);`), add:
```typescript
            identifyUser(profile);
            setUserOptOut(!profile.activity_tracking_enabled);
```

**Step 2: Commit**

```bash
git add -A && git commit -m "feat: identify users in PostHog on login/logout"
```

---

## Task 4: Create backend PostHog helper

**Files:**
- Create: `backend/app/core/posthog.py`

**Step 1: Create PostHog backend client**

Create `backend/app/core/posthog.py`:
```python
"""PostHog analytics client for server-side event tracking.

Fire-and-forget pattern: analytics failures never break business logic.
Uses user_id (internal DB UUID) as distinct_id for person linking.
"""

import logging
from typing import Optional

import posthog as _posthog

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_initialized = False


def init_posthog() -> None:
    """Initialize PostHog client. Call once at app startup."""
    global _initialized
    settings = get_settings()

    if not settings.posthog_enabled or not settings.posthog_api_key:
        logger.info("PostHog disabled (no API key or posthog_enabled=False)")
        return

    _posthog.api_key = settings.posthog_api_key
    _posthog.host = settings.posthog_host
    _posthog.debug = settings.debug
    _initialized = True
    logger.info("PostHog initialized (host=%s)", settings.posthog_host)


def shutdown_posthog() -> None:
    """Flush pending events and shut down. Call at app shutdown."""
    if _initialized:
        _posthog.flush()
        _posthog.shutdown()
        logger.info("PostHog shut down")


def capture(
    user_id: str,
    event: str,
    properties: Optional[dict] = None,
    session_id: Optional[str] = None,
) -> None:
    """Track an event in PostHog (fire-and-forget).

    Args:
        user_id: Internal DB user ID (UUID string) — used as distinct_id.
        event: Event name in noun_verb format (e.g., "session_match_succeeded").
        properties: Event properties dict.
        session_id: If provided, attaches session Group for per-table analytics.
    """
    if not _initialized:
        return

    try:
        props = dict(properties) if properties else {}

        groups = {}
        if session_id:
            groups["session"] = session_id
            props["session_id"] = session_id

        _posthog.capture(
            distinct_id=user_id,
            event=event,
            properties=props,
            groups=groups if groups else None,
        )
    except Exception as e:
        logger.warning("PostHog capture failed for '%s': %s", event, e)


def set_person_properties(user_id: str, properties: dict) -> None:
    """Update person properties in PostHog (e.g., after tier change)."""
    if not _initialized:
        return

    try:
        _posthog.capture(
            distinct_id=user_id,
            event="$set",
            properties={"$set": properties},
        )
    except Exception as e:
        logger.warning("PostHog $set failed: %s", e)
```

**Step 2: Initialize PostHog in app lifespan**

In `backend/app/main.py`:

Add import:
```python
from app.core.posthog import init_posthog, shutdown_posthog
```

In the `lifespan` function, add after `await init_redis()` (line 43):
```python
    init_posthog()
    logger.info("PostHog client initialized")
```

In the shutdown section, add before `await close_redis()` (line 46):
```python
    shutdown_posthog()
```

**Step 3: Commit**

```bash
git add -A && git commit -m "feat: add PostHog backend client with fire-and-forget capture"
```

---

## Task 5: Create type-safe frontend event helpers

**Files:**
- Create: `frontend/src/lib/posthog/events.ts`

**Step 1: Create typed event capture functions**

Create `frontend/src/lib/posthog/events.ts`:

```typescript
/**
 * Type-safe PostHog event capture helpers.
 * Naming convention: noun_verb (e.g., find_table_clicked).
 * One function per event prevents typos and gives autocomplete.
 */
import posthog from "posthog-js";

function capture(event: string, properties?: Record<string, unknown>): void {
  if (!posthog.__loaded) return;
  posthog.capture(event, properties);
}

function captureWithGroup(
  event: string,
  sessionId: string,
  properties?: Record<string, unknown>,
): void {
  if (!posthog.__loaded) return;
  posthog.group("session", sessionId);
  posthog.capture(event, { session_id: sessionId, ...properties });
}

// ─── Auth & Onboarding ──────────────────────────────────────

export function trackAuthLoggedIn(method: string = "google"): void {
  capture("auth_logged_in", { method });
}

export function trackAuthLoggedOut(): void {
  capture("auth_logged_out");
}

export function trackOnboardingStarted(): void {
  capture("onboarding_started");
}

export function trackOnboardingStepViewed(step: number, stepName: string): void {
  capture("onboarding_step_viewed", { step, step_name: stepName });
}

export function trackOnboardingStepCompleted(
  step: number,
  stepName: string,
  selection?: string,
): void {
  capture("onboarding_step_completed", { step, step_name: stepName, selection });
}

// ─── Session Matching ───────────────────────────────────────

export function trackFindTableClicked(mode: string): void {
  capture("find_table_clicked", { mode });
}

export function trackWaitingRoomEntered(sessionId: string, waitMinutes: number): void {
  captureWithGroup("waiting_room_entered", sessionId, { wait_minutes: waitMinutes });
}

export function trackWaitingRoomAbandoned(
  sessionId: string,
  waitedSeconds: number,
  remainingSeconds: number,
): void {
  captureWithGroup("waiting_room_abandoned", sessionId, {
    waited_seconds: waitedSeconds,
    remaining_seconds: remainingSeconds,
  });
}

// ─── Session Lifecycle ──────────────────────────────────────

export function trackMicToggled(sessionId: string, phase: string, enabled: boolean): void {
  captureWithGroup("mic_toggled", sessionId, { phase, enabled });
}

export function trackBoardMessageSent(sessionId: string, phase: string): void {
  captureWithGroup("board_message_sent", sessionId, { phase });
}

export function trackAudioConnected(sessionId: string): void {
  captureWithGroup("audio_connected", sessionId);
}

export function trackAudioDisconnected(sessionId: string, reason?: string): void {
  captureWithGroup("audio_disconnected", sessionId, { reason });
}

// ─── Focus & App Lifecycle ──────────────────────────────────

export function trackAppOpened(referrer?: string): void {
  capture("app_opened", { referrer });
}

export function trackTabFocusChanged(visible: boolean, sessionId?: string): void {
  if (sessionId) {
    captureWithGroup("tab_focus_changed", sessionId, { visible });
  } else {
    capture("tab_focus_changed", { visible });
  }
}

export function trackErrorPageViewed(errorType: string, path: string): void {
  capture("error_page_viewed", { error_type: errorType, path });
}

// ─── Rating & Trust ─────────────────────────────────────────

export function trackRatingPromptViewed(sessionId: string, pendingCount: number): void {
  captureWithGroup("rating_prompt_viewed", sessionId, { pending_count: pendingCount });
}

export function trackRatingPromptDismissed(sessionId: string): void {
  captureWithGroup("rating_prompt_dismissed", sessionId);
}

export function trackBanPageViewed(banRemainingHours: number): void {
  capture("ban_page_viewed", { ban_remaining_hours: banRemainingHours });
}

// ─── Credits & Economy ──────────────────────────────────────

export function trackZeroCreditsViewed(tier: string, nextRefreshDate?: string): void {
  capture("zero_credits_viewed", { tier, next_refresh_date: nextRefreshDate });
}

export function trackUpgradePromptViewed(currentTier: string, context: string): void {
  capture("upgrade_prompt_viewed", { current_tier: currentTier, context });
}

export function trackUpgradeClicked(currentTier: string, targetTier: string): void {
  capture("upgrade_clicked", { current_tier: currentTier, target_tier: targetTier });
}

// ─── Diary & Reflections ────────────────────────────────────

export function trackDiaryViewed(): void {
  capture("diary_viewed");
}

export function trackDiaryEntryViewed(sessionId: string): void {
  capture("diary_entry_viewed", { session_id: sessionId });
}

export function trackReflectionSubmitted(sessionId: string, hasNotes: boolean): void {
  capture("reflection_submitted", { session_id: sessionId, has_notes: hasNotes });
}

// ─── Room & Gamification ────────────────────────────────────

export function trackRoomViewed(isOwnRoom: boolean): void {
  capture("room_viewed", { is_own_room: isOwnRoom });
}

export function trackRoomVisitViewed(visitedUserId: string): void {
  capture("room_visit_viewed", { visited_user_id: visitedUserId });
}

export function trackRoomDecorated(itemType: string): void {
  capture("room_decorated", { item_type: itemType });
}

export function trackShopViewed(): void {
  capture("shop_viewed");
}

export function trackShopItemClicked(itemId: string, itemType: string, price: number): void {
  capture("shop_item_clicked", { item_id: itemId, item_type: itemType, price });
}

export function trackShopPurchaseCompleted(itemId: string, itemType: string, price: number): void {
  capture("shop_purchase_completed", { item_id: itemId, item_type: itemType, price });
}

export function trackTimelineViewed(): void {
  capture("timeline_viewed");
}

// ─── Partners & Social ──────────────────────────────────────

export function trackPartnerListViewed(): void {
  capture("partner_list_viewed");
}

export function trackPartnerInviteClicked(): void {
  capture("partner_invite_clicked");
}

export function trackPartnerScheduleViewed(): void {
  capture("partner_schedule_viewed");
}

// ─── Settings & Profile ─────────────────────────────────────

export function trackProfileViewed(): void {
  capture("profile_viewed");
}

export function trackProfileUpdated(fieldsChanged: string[]): void {
  capture("profile_updated", { fields_changed: fieldsChanged });
}

export function trackLanguageSwitched(fromLocale: string, toLocale: string): void {
  capture("language_switched", { from_locale: fromLocale, to_locale: toLocale });
}

export function trackActivityTrackingToggled(enabled: boolean): void {
  capture("activity_tracking_toggled", { enabled });
}
```

**Step 2: Commit**

```bash
git add -A && git commit -m "feat: add type-safe PostHog event capture helpers"
```

---

## Task 6: Remove old analytics system

**Files:**
- Delete: `backend/app/services/analytics_service.py`
- Modify: `backend/app/routers/analytics.py` (remove all content, keep empty router or delete)
- Modify: `backend/app/main.py` (remove analytics router import + registration)
- Modify: `frontend/src/app/(protected)/session/[sessionId]/waiting/page.tsx` (remove 3 `api.post("/analytics/track")` calls)

**Step 1: Delete backend analytics service**

Delete `backend/app/services/analytics_service.py`.

**Step 2: Remove analytics router**

Delete `backend/app/routers/analytics.py` (the entire file — the endpoint is no longer needed).

**Step 3: Update main.py**

In `backend/app/main.py`:
- Remove `analytics` from the import block (line 15)
- Remove the router registration (line 90): `app.include_router(analytics.router, ...)`

**Step 4: Remove frontend analytics calls from waiting room**

In `frontend/src/app/(protected)/session/[sessionId]/waiting/page.tsx`, there are 3 blocks of `api.post("/analytics/track", ...)` calls:
1. `waiting_room_resumed` event (~lines 35-43)
2. `session_joined_from_waiting_room` event (~lines 72-78)
3. `waiting_room_abandoned` event (~lines 118-127)

Remove all three `api.post("/analytics/track", ...)` blocks. We'll add PostHog replacements in Task 8.

Also remove the `api` import if it's no longer used on this page (check if other `api.` calls remain).

**Step 5: Run backend tests to ensure nothing breaks**

```bash
cd backend && source venv/bin/activate && pytest -x -q
```

If any tests import `AnalyticsService` or reference the `/analytics/track` endpoint, update them to remove those references. Key files to check:
- `backend/tests/` — grep for `analytics_service` and `analytics`

**Step 6: Commit**

```bash
git add -A && git commit -m "refactor: remove custom analytics system (replaced by PostHog)"
```

---

## Task 7: Instrument backend server-side events

**Files:**
- Modify: `backend/app/routers/sessions.py` — 5 endpoints
- Modify: `backend/app/routers/users.py` — 2 endpoints
- Modify: `backend/app/routers/credits.py` — 1 endpoint
- Modify: `backend/app/services/rating_service.py` — rating events

**Step 1: Add PostHog capture to sessions router**

In `backend/app/routers/sessions.py`, add import at top:
```python
from app.core.posthog import capture as posthog_capture
```

Add captures at each success return point:

**quick_match** (before return ~line 300):
```python
    posthog_capture(
        user_id=str(profile.id),
        event="session_match_succeeded",
        properties={
            "mode": match_request.filters.mode if match_request.filters else "forced_audio",
            "wait_minutes": wait_minutes,
            "participant_count": len(session_data.get("participants", [])),
            "is_immediate": is_immediate,
        },
        session_id=str(session_data["id"]),
    )
```

**leave_session** (before return ~line 697):
```python
    posthog_capture(
        user_id=str(profile.id),
        event="session_left_early",
        properties={
            "reason": leave_request.reason if leave_request.reason else "unknown",
        },
        session_id=str(session_id),
    )
```

**cancel_session** (before return ~line 776):
```python
    posthog_capture(
        user_id=str(profile.id),
        event="session_cancelled",
        properties={"credit_refunded": credit_refunded},
        session_id=str(session_id),
    )
```

**rate_participants** (before return ~line 799):
```python
    for r in ratings_request.ratings:
        posthog_capture(
            user_id=str(profile.id),
            event="rating_submitted",
            properties={"rating": r.rating},
            session_id=str(session_id),
        )
```

**skip_ratings** (before return ~line 821):
```python
    posthog_capture(
        user_id=str(profile.id),
        event="rating_prompt_dismissed",
        session_id=str(session_id),
    )
```

**Step 2: Add PostHog capture to users router**

In `backend/app/routers/users.py`, add import:
```python
from app.core.posthog import capture as posthog_capture
```

**get_my_profile** — Track new user creation. The `get_my_profile` endpoint creates users on first call. To detect new vs existing, check if the user was just created. The simplest approach: add a capture after the profile fetch that checks if the user is brand new (not onboarded, first login). Alternatively, track `auth_signed_up` in the `UserService.get_or_create_user` method.

Simpler approach — in `get_my_profile` (around line 51), add a `created_just_now` check:
```python
    # Track new signups (user created in this request)
    # UserService.get_or_create_user returns the profile; if is_onboarded is False
    # and session_count is 0, this is a new user
    if profile.session_count == 0 and not profile.is_onboarded:
        posthog_capture(
            user_id=str(profile.id),
            event="auth_signed_up",
            properties={
                "auth_provider": "google",
                "locale": profile.preferred_language or "en",
            },
        )
```

Note: This fires on every `/users/me` call for un-onboarded users. To prevent duplicates, use PostHog's built-in deduplication or accept that idempotent captures are fine (PostHog handles this).

**update_my_profile** (before return ~line 72):
```python
    posthog_capture(
        user_id=str(profile.id),
        event="profile_updated",
        properties={"fields_changed": [f for f in update.model_dump(exclude_unset=True).keys()]},
    )
```

**Step 3: Add PostHog capture to credits router**

In `backend/app/routers/credits.py`, add import:
```python
from app.core.posthog import capture as posthog_capture
```

The credit_used event should fire in `quick_match` (already handled in sessions router). For `credits_refreshed`, this happens in a scheduled job — add tracking there when the job exists.

For `gift_credits` (before return ~line 87):
```python
    posthog_capture(
        user_id=str(profile.id),
        event="credit_gifted",
        properties={
            "recipient_user_id": str(gift_request.recipient_user_id),
            "amount": gift_request.amount,
        },
    )
```

**Step 4: Run backend tests**

```bash
cd backend && source venv/bin/activate && pytest -x -q
```

If tests fail because `posthog_capture` is called during tests (it shouldn't since `_initialized` will be False), no fix needed. If it does cause issues, the fire-and-forget pattern means tests should still pass.

**Step 5: Commit**

```bash
git add -A && git commit -m "feat: add PostHog server-side event tracking to routers"
```

---

## Task 8: Instrument frontend pages — Session flow

**Files:**
- Modify: `frontend/src/app/(protected)/dashboard/page.tsx`
- Modify: `frontend/src/app/(protected)/session/[sessionId]/waiting/page.tsx`
- Modify: `frontend/src/app/(protected)/session/[sessionId]/page.tsx`
- Modify: `frontend/src/app/(protected)/session/[sessionId]/end/page.tsx`

**Step 1: Dashboard — find_table_clicked**

In `frontend/src/app/(protected)/dashboard/page.tsx`:

Add import:
```typescript
import { trackFindTableClicked } from "@/lib/posthog/events";
```

In `handleJoinSlot` function (around line 142), add right after `setIsMatching(true)`:
```typescript
    trackFindTableClicked(mode);
```

**Step 2: Waiting room — entered, abandoned**

In `frontend/src/app/(protected)/session/[sessionId]/waiting/page.tsx`:

Add import:
```typescript
import { trackWaitingRoomEntered, trackWaitingRoomAbandoned } from "@/lib/posthog/events";
```

Add `trackWaitingRoomEntered` call in the mount effect (where `waiting_room_resumed` was removed). In the useEffect that runs on mount:
```typescript
trackWaitingRoomEntered(sessionId, waitMinutes);
```

In the leave handler (where `waiting_room_abandoned` was removed):
```typescript
trackWaitingRoomAbandoned(sessionId, waitedSeconds, remainingSeconds);
```

Calculate `waitedSeconds` and `remainingSeconds` from the countdown state available in the component.

**Step 3: Session page — mic, board, audio events**

In `frontend/src/app/(protected)/session/[sessionId]/page.tsx`:

Add import:
```typescript
import { trackMicToggled, trackBoardMessageSent, trackAudioConnected, trackAudioDisconnected } from "@/lib/posthog/events";
```

Add `trackMicToggled` where the mute toggle handler is.
Add `trackBoardMessageSent` where board messages are sent.
Add `trackAudioConnected`/`trackAudioDisconnected` where LiveKit connection state changes.

These exact locations depend on the component structure — search for mute/unmute handlers, message send handlers, and LiveKit event listeners within the session page and its sub-components.

**Step 4: Session end — no client events needed (server tracks session_completed)**

The session end page shows a summary. No specific client-side event needed beyond autocaptured pageview.

**Step 5: Commit**

```bash
git add -A && git commit -m "feat: add PostHog tracking to session flow pages"
```

---

## Task 9: Instrument frontend pages — Engagement & Settings

**Files:**
- Modify: `frontend/src/app/(protected)/diary/page.tsx`
- Modify: `frontend/src/app/(protected)/profile/page.tsx`
- Modify: `frontend/src/app/(protected)/room/page.tsx`
- Modify: `frontend/src/app/(protected)/room/visit/[userId]/page.tsx`
- Modify: `frontend/src/app/(protected)/partners/page.tsx`
- Modify: `frontend/src/app/(protected)/banned/page.tsx` (if exists)

**Step 1: Diary page**

Add import + `trackDiaryViewed()` in useEffect on mount.
Add `trackReflectionSubmitted(sessionId, hasNotes)` in the save handler.

**Step 2: Profile page**

Add import + `trackProfileViewed()` in useEffect on mount.
Add `trackProfileUpdated(fieldsChanged)` in the save handler.
Add `trackLanguageSwitched(from, to)` if language switcher is on this page.
Add `trackActivityTrackingToggled(enabled)` when the toggle changes.

**Step 3: Room page**

Add import + `trackRoomViewed(true)` in useEffect on mount (own room).

**Step 4: Room visit page**

Add import + `trackRoomVisitViewed(userId)` in useEffect on mount.

**Step 5: Partners page**

Add import + `trackPartnerListViewed()` in useEffect on mount.
Add `trackPartnerInviteClicked()` in the invite handler.

**Step 6: Banned page (if exists)**

Add `trackBanPageViewed(remainingHours)` on mount.

**Step 7: Commit**

```bash
git add -A && git commit -m "feat: add PostHog tracking to engagement and settings pages"
```

---

## Task 10: Add tab focus tracking

**Files:**
- Modify: `frontend/src/components/providers/posthog-provider.tsx`

**Step 1: Add visibility change listener to PostHogProvider**

In `frontend/src/components/providers/posthog-provider.tsx`, add a `visibilitychange` listener inside the existing useEffect or a new one:

```typescript
import { useSessionStore } from "@/stores/session-store";
import { trackTabFocusChanged } from "@/lib/posthog/events";

// Inside PostHogProvider component, add:
useEffect(() => {
  const handleVisibilityChange = () => {
    const visible = document.visibilityState === "visible";
    const sessionId = useSessionStore.getState().sessionId;
    trackTabFocusChanged(visible, sessionId ?? undefined);
  };

  document.addEventListener("visibilitychange", handleVisibilityChange);
  return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
}, []);
```

**Step 2: Commit**

```bash
git add -A && git commit -m "feat: track tab focus changes for session engagement analysis"
```

---

## Task 11: Backend tests for PostHog helper

**Files:**
- Create: `backend/tests/unit/core/test_posthog.py`

**Step 1: Write tests for the PostHog capture helper**

```python
"""Tests for PostHog analytics helper."""

from unittest.mock import patch, MagicMock

import pytest


class TestPostHogCapture:
    """Test posthog capture helper functions."""

    @patch("app.core.posthog._posthog")
    @patch("app.core.posthog._initialized", True)
    def test_capture_sends_event(self, mock_posthog):
        from app.core.posthog import capture
        capture(user_id="user-123", event="test_event", properties={"key": "val"})
        mock_posthog.capture.assert_called_once()
        call_kwargs = mock_posthog.capture.call_args
        assert call_kwargs.kwargs["distinct_id"] == "user-123"
        assert call_kwargs.kwargs["event"] == "test_event"
        assert call_kwargs.kwargs["properties"]["key"] == "val"

    @patch("app.core.posthog._posthog")
    @patch("app.core.posthog._initialized", True)
    def test_capture_with_session_group(self, mock_posthog):
        from app.core.posthog import capture
        capture(user_id="user-123", event="test_event", session_id="session-456")
        call_kwargs = mock_posthog.capture.call_args
        assert call_kwargs.kwargs["groups"] == {"session": "session-456"}
        assert call_kwargs.kwargs["properties"]["session_id"] == "session-456"

    @patch("app.core.posthog._posthog")
    @patch("app.core.posthog._initialized", False)
    def test_capture_noop_when_not_initialized(self, mock_posthog):
        from app.core.posthog import capture
        capture(user_id="user-123", event="test_event")
        mock_posthog.capture.assert_not_called()

    @patch("app.core.posthog._posthog")
    @patch("app.core.posthog._initialized", True)
    def test_capture_swallows_exceptions(self, mock_posthog):
        from app.core.posthog import capture
        mock_posthog.capture.side_effect = Exception("network error")
        # Should not raise
        capture(user_id="user-123", event="test_event")

    @patch("app.core.posthog._posthog")
    @patch("app.core.posthog._initialized", True)
    def test_set_person_properties(self, mock_posthog):
        from app.core.posthog import set_person_properties
        set_person_properties("user-123", {"tier": "pro"})
        call_kwargs = mock_posthog.capture.call_args
        assert call_kwargs.kwargs["event"] == "$set"
        assert call_kwargs.kwargs["properties"]["$set"]["tier"] == "pro"
```

**Step 2: Run tests**

```bash
cd backend && source venv/bin/activate && pytest tests/unit/core/test_posthog.py -v
```

**Step 3: Commit**

```bash
git add -A && git commit -m "test: add unit tests for PostHog capture helper"
```

---

## Task 12: Frontend build verification + manual test

**Step 1: Run frontend lint and build**

```bash
cd frontend && npm run lint && npm run build
```

Fix any TypeScript errors or import issues.

**Step 2: Run frontend tests**

```bash
cd frontend && npm run test
```

Fix any failing tests. Common issues:
- Tests that import pages with new PostHog imports may need `posthog-js` mocked in `setup.ts`
- Add to `frontend/src/test/setup.ts` if needed:
```typescript
vi.mock("posthog-js", () => ({
  default: {
    init: vi.fn(),
    capture: vi.fn(),
    identify: vi.fn(),
    reset: vi.fn(),
    group: vi.fn(),
    opt_out_capturing: vi.fn(),
    opt_in_capturing: vi.fn(),
    __loaded: false,
  },
}));
```

**Step 3: Run backend tests**

```bash
cd backend && source venv/bin/activate && pytest -x -q
```

**Step 4: Manual verification**

1. Start backend: `cd backend && uvicorn main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Open browser devtools Network tab
4. Log in — verify PostHog requests are sent to `us.i.posthog.com` (or see console log if no API key)
5. Navigate between pages — verify `$pageview` events fire
6. Check PostHog dashboard (if configured) → Live Events to see events flowing

**Step 5: Commit any fixes**

```bash
git add -A && git commit -m "fix: resolve build and test issues from PostHog integration"
```

---

## Task 13: Update environment configuration

**Files:**
- Modify: `frontend/.env.example`
- Modify: `backend/.env.example` (or equivalent)
- Modify: deployment configs if they exist

**Step 1: Document required env vars**

Ensure `.env.example` files include PostHog vars (done in Task 1).

For actual deployment (Vercel + Railway), the user needs to set:
- Vercel: `NEXT_PUBLIC_POSTHOG_KEY`, `NEXT_PUBLIC_POSTHOG_HOST`
- Railway: `POSTHOG_API_KEY`, `POSTHOG_HOST`

**Step 2: Final commit**

```bash
git add -A && git commit -m "docs: update env examples with PostHog configuration"
```

---

## Summary

| Task | Description | Est. Changes |
|------|-------------|-------------|
| 1 | Install dependencies + config | 4 files |
| 2 | Frontend provider + client | 4 files (3 new, 1 modify) |
| 3 | Auth identify + consent | 1 file |
| 4 | Backend PostHog helper | 2 files (1 new, 1 modify) |
| 5 | Type-safe event helpers | 1 file (new) |
| 6 | Remove old analytics | 4 files (2 delete, 2 modify) |
| 7 | Backend server-side events | 3 files |
| 8 | Frontend session flow events | 3-4 files |
| 9 | Frontend engagement events | 5-6 files |
| 10 | Tab focus tracking | 1 file |
| 11 | Backend PostHog tests | 1 file (new) |
| 12 | Build verification + manual test | Fix files as needed |
| 13 | Environment docs | 1-2 files |

**Total: ~13 tasks, ~25-30 files touched, ~52 events instrumented**
