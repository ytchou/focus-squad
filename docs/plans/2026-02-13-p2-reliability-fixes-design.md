# P2 Reliability Fixes Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 4 medium-priority reliability issues: essence purchase race conditions, partner cache for RLS performance, message cursor reset, and analytics retention policy.

**Architecture:** Database-level transaction for essence atomicity, Redis caching for partner lookups, frontend state cleanup for cursors, Celery scheduled task for analytics cleanup.

**Tech Stack:** PostgreSQL functions, Redis, Zustand, Celery Beat

---

## 1. Essence Purchase Transaction Atomicity

### Problem

Current flow has a gap between essence deduction and inventory insertion. If inventory insert fails AND the refund RPC fails, user loses essence permanently. The refund failure is caught and logged but not re-raised.

### Solution

Create a PostgreSQL function `purchase_item_atomic` that wraps all operations in a single transaction with `SELECT FOR UPDATE` row locking.

### Database Function

```sql
CREATE OR REPLACE FUNCTION purchase_item_atomic(
    p_user_id UUID,
    p_item_id UUID,
    p_is_gift BOOLEAN DEFAULT FALSE,
    p_recipient_id UUID DEFAULT NULL
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_cost INTEGER;
    v_item_type TEXT;
    v_balance INTEGER;
    v_inventory_id UUID;
BEGIN
    -- 1. Get item cost (fail if not found)
    SELECT cost, item_type INTO v_cost, v_item_type
    FROM shop_items WHERE id = p_item_id;

    IF v_cost IS NULL THEN
        RETURN json_build_object('success', false, 'error', 'item_not_found');
    END IF;

    -- 2. Lock user's essence row and check balance
    SELECT balance INTO v_balance
    FROM furniture_essence
    WHERE user_id = p_user_id
    FOR UPDATE;

    IF v_balance IS NULL OR v_balance < v_cost THEN
        RETURN json_build_object('success', false, 'error', 'insufficient_essence');
    END IF;

    -- 3. Deduct essence
    UPDATE furniture_essence
    SET balance = balance - v_cost,
        total_spent = total_spent + v_cost,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    -- 4. Insert inventory item
    INSERT INTO user_items (user_id, item_id, gifted_by)
    VALUES (
        COALESCE(p_recipient_id, p_user_id),
        p_item_id,
        CASE WHEN p_is_gift THEN p_user_id ELSE NULL END
    )
    RETURNING id INTO v_inventory_id;

    -- 5. Log transaction
    INSERT INTO essence_transactions (user_id, amount, transaction_type, related_item_id)
    VALUES (p_user_id, -v_cost,
            CASE WHEN p_is_gift THEN 'item_gift' ELSE 'item_purchase' END,
            p_item_id);

    RETURN json_build_object(
        'success', true,
        'inventory_id', v_inventory_id,
        'new_balance', v_balance - v_cost
    );
END;
$$;
```

### Service Changes

Replace `buy_item()` and `gift_item()` in `essence_service.py` to call this single RPC instead of separate deduct → insert → log operations.

### Benefits

- **Atomicity**: All-or-nothing - no partial state possible
- **No refund logic needed**: Transaction rollback handles failures
- **Row locking**: `FOR UPDATE` prevents concurrent purchases from same user

---

## 2. Partner Lists Caching

### Problem

RLS policies for partner content viewing execute 3 nested subqueries per-row. The bidirectional OR pattern (`requester_id=X OR addressee_id=X`) prevents efficient index usage.

### Solution

Cache accepted partner IDs in Redis with 5-minute TTL. Invalidate on partnership changes.

### Cache Design

**Key Pattern:** `partners:{user_id}:accepted`
**Data Structure:** Redis SET (for O(1) membership checks)
**TTL:** 300 seconds (5 minutes)

### Implementation

```python
class PartnerService:
    PARTNER_CACHE_TTL = 300  # 5 minutes

    async def get_accepted_partner_ids(self, user_id: str) -> set[str]:
        """Get partner IDs with Redis cache."""
        cache_key = f"partners:{user_id}:accepted"

        # Try cache first
        cached = await self.redis.smembers(cache_key)
        if cached:
            return cached

        # Cache miss - query DB
        result = self.supabase.table("partnerships") \
            .select("requester_id, addressee_id") \
            .or_(f"requester_id.eq.{user_id},addressee_id.eq.{user_id}") \
            .eq("status", "accepted") \
            .execute()

        partner_ids = set()
        for row in result.data or []:
            other_id = row["addressee_id"] if row["requester_id"] == user_id else row["requester_id"]
            partner_ids.add(other_id)

        # Cache result
        if partner_ids:
            await self.redis.sadd(cache_key, *partner_ids)
            await self.redis.expire(cache_key, self.PARTNER_CACHE_TTL)

        return partner_ids

    def _invalidate_partner_cache(self, user_id: str) -> None:
        """Invalidate cache on partnership changes."""
        self.redis.delete(f"partners:{user_id}:accepted")
```

### Invalidation Points

Call `_invalidate_partner_cache()` for both users in:
- `send_request()` - status changes to pending
- `respond_to_request()` - accepted/rejected
- `remove_partner()` - partnership deleted

### Benefits

- **O(1) lookups**: Redis SET membership check
- **5-min TTL**: Handles missed invalidations gracefully
- **No schema change**: Uses existing Redis infrastructure

---

## 3. Message Cursor Reset

### Problem

When switching conversations, old pagination cursors persist in the Zustand store. Returning to a previous conversation with a stale cursor could skip messages or cause errors.

### Solution

Clear pagination state for the previous conversation when opening a new one.

### Implementation

```typescript
// In message-store.ts openConversation:

openConversation: async (id: string) => {
  const prevId = get().activeConversationId;

  // Clear pagination state for previous conversation
  if (prevId && prevId !== id) {
    set((state) => ({
      cursors: { ...state.cursors, [prevId]: null },
      hasMore: { ...state.hasMore, [prevId]: true },
    }));
  }

  set({ activeConversationId: id, isLoadingMessages: true });

  // ... rest of existing fetch logic
}
```

### Benefits

- **Fresh pagination**: Re-entering a conversation starts from most recent
- **No backend changes**: Pure frontend fix
- **Minimal code change**: 6 lines added

---

## 4. Analytics Retention Policy

### Problem

`session_analytics_events` table grows unbounded. No TTL or cleanup mechanism exists.

### Solution

Daily Celery task to delete events older than 1 year, using batch deletes to avoid lock contention.

### Database Function

```sql
CREATE OR REPLACE FUNCTION delete_old_analytics(
    cutoff_interval INTERVAL DEFAULT '1 year',
    batch_limit INTEGER DEFAULT 1000
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    WITH to_delete AS (
        SELECT id FROM session_analytics_events
        WHERE created_at < NOW() - cutoff_interval
        LIMIT batch_limit
    )
    DELETE FROM session_analytics_events
    WHERE id IN (SELECT id FROM to_delete);

    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN json_build_object('deleted', v_deleted);
END;
$$;
```

### Celery Task

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def cleanup_old_analytics(self):
    """Delete analytics events older than 1 year. Batch deletes."""
    supabase = get_supabase()
    batch_size = 1000
    total_deleted = 0

    while True:
        result = supabase.rpc(
            "delete_old_analytics",
            {"cutoff_interval": "1 year", "batch_limit": batch_size}
        ).execute()

        deleted_count = result.data.get("deleted", 0) if result.data else 0
        total_deleted += deleted_count

        if deleted_count < batch_size:
            break

    logger.info(f"Analytics cleanup: deleted {total_deleted} events")
    return {"deleted": total_deleted}
```

### Celery Beat Schedule

```python
"cleanup-old-analytics": {
    "task": "app.tasks.analytics_tasks.cleanup_old_analytics",
    "schedule": crontab(hour=2, minute=0),  # 02:00 UTC daily
},
```

### Benefits

- **Batch delete**: Avoids table locks (1000 rows at a time)
- **Off-peak**: 02:00 UTC is ~10:00 AM Taiwan, low traffic
- **1-year retention**: Balances analytics value vs storage

---

## Testing Strategy

### Essence Purchase
- Test concurrent purchases (same user) - should serialize via row lock
- Test insufficient balance - should return error, no side effects
- Test gift flow - recipient gets item, sender pays

### Partner Cache
- Test cache hit/miss behavior
- Test invalidation on partnership changes
- Test TTL expiration

### Message Cursor
- Test switching conversations clears previous cursor
- Test re-entering conversation fetches fresh messages

### Analytics Cleanup
- Test batch deletion with mock data
- Test cleanup task scheduling
- Test retry on failure

---

## Files to Modify

### Backend
- `supabase/migrations/XXX_atomic_essence_purchase.sql` - New RPC
- `supabase/migrations/XXX_analytics_retention.sql` - New RPC
- `backend/app/services/essence_service.py` - Use atomic RPC
- `backend/app/services/partner_service.py` - Add Redis cache
- `backend/app/tasks/analytics_tasks.py` - New cleanup task
- `backend/app/core/celery_app.py` - Add beat schedule

### Frontend
- `frontend/src/stores/message-store.ts` - Cursor reset logic

### Tests
- `backend/tests/unit/services/test_essence_service.py` - Atomic purchase tests
- `backend/tests/unit/services/test_partner_service.py` - Cache tests
- `backend/tests/unit/tasks/test_analytics_tasks.py` - Cleanup tests
- `frontend/src/stores/__tests__/message-store.test.ts` - Cursor reset tests
