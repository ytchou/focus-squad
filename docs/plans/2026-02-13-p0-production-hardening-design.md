# Phase 5 P0: Production Hardening Design

**Date:** 2026-02-13
**Status:** Approved
**Priority:** P0 — Blocking for alpha launch

---

## Overview

Four critical hardening tasks to ensure Focus Squad doesn't fail silently in production:

1. **Startup Secret Validation** — Prevent app from starting with missing credentials
2. **JWKS Cache TTL** — Handle Supabase key rotation without restarts
3. **Redis Connection Test** — Detect Redis failures early with retry
4. **Rating SessionId Validation** — Prevent wrong-session ratings (defense in depth)

---

## 1. Startup Secret Validation

### Problem
`config.py` uses empty string defaults for secrets. App starts without credentials, fails at runtime with confusing errors.

### Solution
Add Pydantic `@model_validator` to `Settings` class that validates required secrets on initialization.

**Required secrets:**
- `supabase_url`
- `supabase_anon_key`
- `supabase_service_role_key`
- `livekit_api_key`
- `livekit_api_secret`
- `livekit_url`

**Behavior:**
- If any required secret is empty string → raise `ValueError`
- Error message lists ALL missing secrets (not just first)
- `jwt_secret` remains optional (unused — auth uses JWKS)

**Error example:**
```
ValueError: Missing required secrets: SUPABASE_URL, LIVEKIT_API_KEY
Set these environment variables before starting the application.
```

### Files
- `backend/app/core/config.py`

### Tests
- Missing one secret → ValueError with that secret listed
- Missing multiple secrets → ValueError with all listed
- All secrets present → Settings loads successfully
- Empty string treated same as missing

---

## 2. JWKS Cache with Background Refresh

### Problem
Global `_jwks_cache` in `auth.py` never expires. If Supabase rotates keys, auth breaks until app restart.

### Solution
Create `JWKSCache` class with 1-hour TTL and proactive background refresh.

**Design:**
```
┌─────────────────────────────────────────────────────────┐
│                    JWKSCache class                       │
├─────────────────────────────────────────────────────────┤
│ _keys: dict | None          # Cached JWKS data          │
│ _fetched_at: float | None   # Timestamp of last fetch   │
│ _refresh_task: Task | None  # Background refresh task   │
│ _lock: asyncio.Lock         # Prevent concurrent fetch  │
│                                                         │
│ TTL = 3600 seconds (1 hour)                             │
│ REFRESH_BEFORE = 300 seconds (5 min before expiry)      │
├─────────────────────────────────────────────────────────┤
│ async get_keys() -> dict                                │
│ async _fetch_keys() -> dict                             │
│ _schedule_background_refresh() -> None                  │
│ invalidate() -> None                                    │
└─────────────────────────────────────────────────────────┘
```

**Behavior:**
1. First request: synchronous fetch, cache result
2. Request at T+55 min: return cached keys, spawn background task
3. Background task fetches new keys, updates cache
4. If background fetch fails: log warning, keep old keys (still valid)
5. If cache fully expired AND no background ran: sync fetch (rare fallback)

**Thread safety:** `asyncio.Lock` prevents multiple concurrent fetches.

**Note:** Functions using JWKS (`get_signing_key`, `decode_supabase_token`) need to become async to use the new cache.

### Files
- `backend/app/core/auth.py`

### Tests
- Fresh cache returns without fetch
- Cache at 55 min triggers background refresh
- Expired cache falls back to sync fetch
- Concurrent access uses lock (no duplicate fetches)
- Background fetch failure keeps old keys
- `invalidate()` clears cache

---

## 3. Redis Connection Validation with Retry

### Problem
`init_redis()` creates connection pool but never verifies Redis is reachable. Silent failure if Redis down.

### Solution
Add ping with exponential backoff retry to `init_redis()`.

**Behavior:**
- Attempt 1: ping → fail → wait 1s
- Attempt 2: ping → fail → wait 2s
- Attempt 3: ping → fail → raise `RuntimeError`
- Total max wait: 7 seconds

**Error:**
```
RuntimeError: Redis connection failed after 3 attempts: Connection refused
```

**Rationale:**
- 3 retries handles brief network blips during deployment
- 7 seconds is reasonable startup delay
- Hard fail lets orchestrators (Railway, K8s) detect and respond

### Files
- `backend/app/core/redis.py`

### Tests
- Successful ping on first try → no retries
- Success on retry 2 → logged warning, continues
- Failure after 3 attempts → RuntimeError raised
- Delays are correct (1s, 2s, 4s)

---

## 4. Rating SessionId Validation

### Problem
`rating-store.ts` holds `pendingSessionId` but `submitRatings(sessionId)` accepts any sessionId parameter. Could submit ratings for wrong session if page has stale state.

### Current Backend Protection
`rating_service.submit_ratings()` already validates:
- User must be participant in that session
- Session must be in "social" or "ended" phase
- Ratees must be human participants

Backend is secure — but error messages are confusing for UX.

### Solution
Add frontend guard for immediate feedback.

**Frontend (`rating-store.ts`):**
```typescript
submitRatings: async (sessionId) => {
  const { pendingSessionId } = get();

  if (pendingSessionId && sessionId !== pendingSessionId) {
    set({ error: "Session mismatch: cannot rate a different session" });
    return;
  }

  // ... existing implementation
}
```

Same guard for `skipAll()`.

### Files
- `frontend/src/stores/rating-store.ts`

### Tests
- Matching sessionId → proceeds normally
- Mismatched sessionId → sets error, no API call
- No pendingSessionId set → proceeds (edge case)

---

## Implementation Order

1. **Startup Secret Validation** — Simplest, immediate value
2. **Redis Connection Test** — Simple, builds on startup validation pattern
3. **Rating SessionId Validation** — Frontend-only, quick win
4. **JWKS Cache TTL** — Most complex, requires async refactor

---

## Verification Checklist

- [ ] All 4 features implemented with tests
- [ ] Backend tests pass (target: 650+)
- [ ] Frontend tests pass (target: 360+)
- [ ] App starts successfully with all secrets
- [ ] App fails clearly with missing secrets
- [ ] Manual test: JWKS cache refresh doesn't block requests
- [ ] Manual test: Redis retry works during brief outage
