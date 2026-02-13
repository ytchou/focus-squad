# P2 Reliability Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix 4 medium-priority reliability issues: essence purchase race conditions, partner cache for RLS performance, message cursor reset, and analytics retention policy.

**Architecture:** Database-level transaction for essence atomicity, Redis caching for partner lookups, frontend state cleanup for cursors, Celery scheduled task for analytics cleanup.

**Tech Stack:** PostgreSQL functions, Redis, Zustand, Celery Beat

---

## Task 1: Atomic Essence Purchase - Database Migration

**Files:**
- Create: `supabase/migrations/031_atomic_essence_purchase.sql`

**Step 1: Create the migration file**

```sql
-- Migration: 031_atomic_essence_purchase.sql
-- Purpose: Atomic item purchase/gift RPC that wraps all operations in a single transaction

CREATE OR REPLACE FUNCTION purchase_item_atomic(
    p_user_id UUID,
    p_item_id UUID,
    p_is_gift BOOLEAN DEFAULT FALSE,
    p_recipient_id UUID DEFAULT NULL,
    p_gift_message TEXT DEFAULT NULL
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_cost INTEGER;
    v_item_name TEXT;
    v_balance INTEGER;
    v_inventory_id UUID;
    v_target_user_id UUID;
BEGIN
    -- 1. Get item cost and name (fail if not found or unavailable)
    SELECT essence_cost, name INTO v_cost, v_item_name
    FROM items
    WHERE id = p_item_id
      AND is_available = TRUE
      AND is_purchasable = TRUE;

    IF v_cost IS NULL THEN
        RETURN json_build_object('success', false, 'error', 'item_not_found');
    END IF;

    -- 2. Lock user's essence row and check balance (prevents concurrent purchases)
    SELECT balance INTO v_balance
    FROM furniture_essence
    WHERE user_id = p_user_id
    FOR UPDATE;

    IF v_balance IS NULL THEN
        RETURN json_build_object('success', false, 'error', 'no_essence_record');
    END IF;

    IF v_balance < v_cost THEN
        RETURN json_build_object('success', false, 'error', 'insufficient_essence');
    END IF;

    -- 3. Deduct essence from buyer
    UPDATE furniture_essence
    SET balance = balance - v_cost,
        total_spent = total_spent + v_cost,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    -- 4. Determine target user for inventory
    v_target_user_id := COALESCE(p_recipient_id, p_user_id);

    -- 5. Insert inventory item
    INSERT INTO user_items (user_id, item_id, acquisition_type, gifted_by, gift_message)
    VALUES (
        v_target_user_id,
        p_item_id,
        CASE WHEN p_is_gift THEN 'gift' ELSE 'purchased' END,
        CASE WHEN p_is_gift THEN p_user_id ELSE NULL END,
        CASE WHEN p_is_gift THEN p_gift_message ELSE NULL END
    )
    RETURNING id INTO v_inventory_id;

    -- 6. Log transaction
    INSERT INTO essence_transactions (user_id, amount, transaction_type, description, related_item_id)
    VALUES (
        p_user_id,
        -v_cost,
        CASE WHEN p_is_gift THEN 'item_gift' ELSE 'item_purchase' END,
        CASE WHEN p_is_gift
            THEN 'Gifted ' || v_item_name
            ELSE 'Purchased ' || v_item_name
        END,
        p_item_id
    );

    RETURN json_build_object(
        'success', true,
        'inventory_id', v_inventory_id,
        'new_balance', v_balance - v_cost,
        'item_name', v_item_name,
        'cost', v_cost
    );
END;
$$;

-- Add comment for documentation
COMMENT ON FUNCTION purchase_item_atomic IS
'Atomic item purchase that wraps essence deduction, inventory insert, and transaction logging in a single transaction. Uses FOR UPDATE row lock to prevent race conditions.';
```

**Step 2: Verify migration syntax**

Run: `cd /Users/ytchou/Project/focus-squad && cat supabase/migrations/031_atomic_essence_purchase.sql | head -20`
Expected: See the CREATE OR REPLACE FUNCTION header

**Step 3: Commit**

```bash
git add supabase/migrations/031_atomic_essence_purchase.sql
git commit -m "feat(db): add atomic essence purchase RPC with transaction safety"
```

---

## Task 2: Atomic Essence Purchase - Service Refactor

**Files:**
- Modify: `backend/app/services/essence_service.py`
- Test: `backend/tests/unit/services/test_essence_service.py`

**Step 1: Write the failing tests**

Add to `backend/tests/unit/services/test_essence_service.py`:

```python
class TestAtomicPurchase:
    """Tests for atomic purchase_item_atomic RPC integration."""

    def test_buy_item_uses_atomic_rpc(self, essence_service: EssenceService, mock_supabase: MagicMock):
        """buy_item should call purchase_item_atomic RPC."""
        # Setup mock
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={"success": True, "inventory_id": "inv-123", "new_balance": 95, "item_name": "Desk Lamp", "cost": 5}
        )

        result = essence_service.buy_item("user-1", "item-1")

        # Verify RPC was called with correct params
        mock_supabase.rpc.assert_called_once_with(
            "purchase_item_atomic",
            {"p_user_id": "user-1", "p_item_id": "item-1", "p_is_gift": False, "p_recipient_id": None, "p_gift_message": None}
        )
        assert result.id == "inv-123"

    def test_buy_item_insufficient_essence_from_rpc(self, essence_service: EssenceService, mock_supabase: MagicMock):
        """buy_item should raise InsufficientEssenceError when RPC returns insufficient_essence."""
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={"success": False, "error": "insufficient_essence"}
        )

        with pytest.raises(InsufficientEssenceError):
            essence_service.buy_item("user-1", "item-1")

    def test_buy_item_item_not_found_from_rpc(self, essence_service: EssenceService, mock_supabase: MagicMock):
        """buy_item should raise ItemNotFoundError when RPC returns item_not_found."""
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={"success": False, "error": "item_not_found"}
        )

        with pytest.raises(ItemNotFoundError):
            essence_service.buy_item("user-1", "item-1")

    def test_gift_item_uses_atomic_rpc(self, essence_service: EssenceService, mock_supabase: MagicMock):
        """gift_item should call purchase_item_atomic RPC with gift params."""
        # Mock partnership check
        mock_supabase.table.return_value.select.return_value.eq.return_value.or_.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "partnership-1"}]
        )
        # Mock recipient lookup
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"display_name": "Partner", "username": "partner"}]
        )
        # Mock RPC
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={"success": True, "inventory_id": "inv-456", "new_balance": 90, "item_name": "Plant", "cost": 10}
        )

        result = essence_service.gift_item("sender-1", "recipient-1", "item-1", "Happy birthday!")

        # Verify RPC called with gift params
        mock_supabase.rpc.assert_called_with(
            "purchase_item_atomic",
            {"p_user_id": "sender-1", "p_item_id": "item-1", "p_is_gift": True, "p_recipient_id": "recipient-1", "p_gift_message": "Happy birthday!"}
        )
        assert result.inventory_item_id == "inv-456"
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/ytchou/Project/focus-squad/backend && source venv/bin/activate && pytest tests/unit/services/test_essence_service.py::TestAtomicPurchase -v`
Expected: FAIL (tests reference new behavior not yet implemented)

**Step 3: Refactor buy_item to use atomic RPC**

Replace the `buy_item` method in `backend/app/services/essence_service.py` (lines 87-152):

```python
def buy_item(self, user_id: str, item_id: str) -> InventoryItem:
    """
    Purchase an item using atomic RPC.

    The purchase_item_atomic RPC handles:
    - Item lookup and availability check
    - Balance check with row lock (FOR UPDATE)
    - Essence deduction
    - Inventory insertion
    - Transaction logging

    All in a single atomic transaction - if any step fails, nothing is committed.
    """
    result = self.supabase.rpc(
        "purchase_item_atomic",
        {
            "p_user_id": user_id,
            "p_item_id": item_id,
            "p_is_gift": False,
            "p_recipient_id": None,
            "p_gift_message": None,
        },
    ).execute()

    if not result.data:
        raise EssenceServiceError("Purchase failed: no response from database")

    data = result.data
    if not data.get("success"):
        error = data.get("error", "unknown_error")
        if error == "item_not_found":
            raise ItemNotFoundError(f"Item {item_id} not found or unavailable")
        elif error == "insufficient_essence":
            raise InsufficientEssenceError("Insufficient essence for this purchase")
        elif error == "no_essence_record":
            raise InsufficientEssenceError("No essence balance found")
        else:
            raise EssenceServiceError(f"Purchase failed: {error}")

    # Fetch item details for response (RPC returns minimal data)
    item_result = self.supabase.table("items").select("*").eq("id", item_id).execute()
    item_data = item_result.data[0] if item_result.data else {}

    return InventoryItem(
        id=data["inventory_id"],
        item_id=item_id,
        item=ShopItem(**item_data) if item_data else None,
        acquired_at=None,  # Will be set by DB default
        acquisition_type="purchased",
    )
```

**Step 4: Refactor gift_item to use atomic RPC**

Replace the `gift_item` method (lines 154-261):

```python
def gift_item(
    self,
    sender_id: str,
    recipient_id: str,
    item_id: str,
    gift_message: Optional[str] = None,
) -> GiftPurchaseResponse:
    """
    Gift an item to a partner using atomic RPC.

    Validates partnership first, then uses purchase_item_atomic RPC for
    atomic essence deduction and inventory insertion.
    """
    if sender_id == recipient_id:
        raise SelfGiftError("Cannot gift an item to yourself.")

    # Verify accepted partnership (must check before RPC)
    partnership_result = (
        self.supabase.table("partnerships")
        .select("id")
        .eq("status", "accepted")
        .or_(
            f"and(requester_id.eq.{sender_id},addressee_id.eq.{recipient_id}),"
            f"and(requester_id.eq.{recipient_id},addressee_id.eq.{sender_id})"
        )
        .limit(1)
        .execute()
    )
    if not partnership_result.data:
        raise NotPartnerError("You must be partners to gift items.")

    # Look up recipient name for response
    recipient_result = (
        self.supabase.table("users")
        .select("display_name, username")
        .eq("id", recipient_id)
        .execute()
    )
    recipient_data = recipient_result.data[0] if recipient_result.data else {}
    recipient_name = recipient_data.get("display_name") or recipient_data.get("username", "Unknown")

    # Atomic purchase via RPC
    result = self.supabase.rpc(
        "purchase_item_atomic",
        {
            "p_user_id": sender_id,
            "p_item_id": item_id,
            "p_is_gift": True,
            "p_recipient_id": recipient_id,
            "p_gift_message": gift_message,
        },
    ).execute()

    if not result.data:
        raise EssenceServiceError("Gift purchase failed: no response from database")

    data = result.data
    if not data.get("success"):
        error = data.get("error", "unknown_error")
        if error == "item_not_found":
            raise ItemNotFoundError(f"Item {item_id} not found or unavailable")
        elif error == "insufficient_essence":
            raise InsufficientEssenceError("Insufficient essence to gift this item")
        elif error == "no_essence_record":
            raise InsufficientEssenceError("No essence balance found")
        else:
            raise EssenceServiceError(f"Gift purchase failed: {error}")

    return GiftPurchaseResponse(
        inventory_item_id=data["inventory_id"],
        item_name=data.get("item_name", "Item"),
        recipient_name=recipient_name,
        essence_spent=data.get("cost", 0),
    )
```

**Step 5: Remove _refund_essence method**

Delete the `_refund_essence` method (lines 300-327) - no longer needed with atomic transactions.

**Step 6: Run tests to verify they pass**

Run: `cd /Users/ytchou/Project/focus-squad/backend && pytest tests/unit/services/test_essence_service.py -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add backend/app/services/essence_service.py backend/tests/unit/services/test_essence_service.py
git commit -m "refactor(essence): use atomic RPC for purchases, remove refund logic"
```

---

## Task 3: Partner Cache - Redis Integration

**Files:**
- Modify: `backend/app/services/partner_service.py`
- Test: `backend/tests/unit/services/test_partner_service.py`

**Step 1: Write the failing tests**

Add to `backend/tests/unit/services/test_partner_service.py`:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestPartnerCache:
    """Tests for Redis partner cache."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis = MagicMock()
        redis.smembers = MagicMock(return_value=set())
        redis.sadd = MagicMock()
        redis.expire = MagicMock()
        redis.delete = MagicMock()
        return redis

    def test_get_accepted_partner_ids_cache_miss(
        self, partner_service: PartnerService, mock_supabase: MagicMock, mock_redis: MagicMock
    ):
        """On cache miss, should query DB and cache result."""
        partner_service._redis = mock_redis
        mock_redis.smembers.return_value = set()  # Cache miss

        # Mock DB response
        mock_supabase.table.return_value.select.return_value.or_.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[
                {"requester_id": "user-1", "addressee_id": "partner-1"},
                {"requester_id": "partner-2", "addressee_id": "user-1"},
            ]
        )

        result = partner_service.get_accepted_partner_ids("user-1")

        assert result == {"partner-1", "partner-2"}
        mock_redis.sadd.assert_called_once()
        mock_redis.expire.assert_called_once_with("partners:user-1:accepted", 300)

    def test_get_accepted_partner_ids_cache_hit(
        self, partner_service: PartnerService, mock_supabase: MagicMock, mock_redis: MagicMock
    ):
        """On cache hit, should return cached data without DB query."""
        partner_service._redis = mock_redis
        mock_redis.smembers.return_value = {"partner-1", "partner-2"}  # Cache hit

        result = partner_service.get_accepted_partner_ids("user-1")

        assert result == {"partner-1", "partner-2"}
        mock_supabase.table.assert_not_called()

    def test_invalidate_partner_cache(
        self, partner_service: PartnerService, mock_redis: MagicMock
    ):
        """Should delete cache key for user."""
        partner_service._redis = mock_redis

        partner_service._invalidate_partner_cache("user-1")

        mock_redis.delete.assert_called_once_with("partners:user-1:accepted")

    def test_respond_to_request_invalidates_cache(
        self, partner_service: PartnerService, mock_supabase: MagicMock, mock_redis: MagicMock
    ):
        """Accepting a request should invalidate cache for both users."""
        partner_service._redis = mock_redis

        # Mock existing pending request
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "p-1", "requester_id": "user-a", "addressee_id": "user-b", "status": "pending"}]
        )
        # Mock update
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "p-1", "status": "accepted"}]
        )

        partner_service.respond_to_request("p-1", "user-b", accept=True)

        # Both users' caches should be invalidated
        assert mock_redis.delete.call_count == 2
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/ytchou/Project/focus-squad/backend && pytest tests/unit/services/test_partner_service.py::TestPartnerCache -v`
Expected: FAIL (methods don't exist yet)

**Step 3: Add Redis to PartnerService**

Modify `backend/app/services/partner_service.py` - add imports and cache methods:

```python
# Add to imports at top of file
from app.core.redis import get_redis

# Add constant after logger
PARTNER_CACHE_TTL = 300  # 5 minutes

# Modify __init__ to add Redis
def __init__(self, supabase: Optional[Client] = None, redis: Optional[object] = None) -> None:
    self._supabase = supabase
    self._redis = redis

@property
def redis(self):
    if self._redis is None:
        self._redis = get_redis()
    return self._redis

# Add new methods after __init__
def get_accepted_partner_ids(self, user_id: str) -> set[str]:
    """
    Get accepted partner IDs with Redis cache.

    Uses Redis SET for O(1) membership checks.
    TTL of 5 minutes handles missed invalidations.
    """
    cache_key = f"partners:{user_id}:accepted"

    # Try cache first
    cached = self.redis.smembers(cache_key)
    if cached:
        return cached

    # Cache miss - query DB
    result = (
        self.supabase.table("partnerships")
        .select("requester_id, addressee_id")
        .or_(f"requester_id.eq.{user_id},addressee_id.eq.{user_id}")
        .eq("status", "accepted")
        .execute()
    )

    partner_ids: set[str] = set()
    for row in result.data or []:
        other_id = row["addressee_id"] if row["requester_id"] == user_id else row["requester_id"]
        partner_ids.add(other_id)

    # Cache result (only if non-empty)
    if partner_ids:
        self.redis.sadd(cache_key, *partner_ids)
        self.redis.expire(cache_key, PARTNER_CACHE_TTL)

    return partner_ids

def _invalidate_partner_cache(self, user_id: str) -> None:
    """Invalidate partner cache for a user."""
    self.redis.delete(f"partners:{user_id}:accepted")
```

**Step 4: Add cache invalidation calls**

In `send_request()` (after line 100, after the insert):
```python
# Invalidate cache for both users
self._invalidate_partner_cache(requester_id)
self._invalidate_partner_cache(addressee_id)
```

In `respond_to_request()` (after the update, around line 140):
```python
# Invalidate cache for both users
self._invalidate_partner_cache(requester_id)
self._invalidate_partner_cache(addressee_id)
```

In `remove_partner()` (after deletion, around line 200):
```python
# Invalidate cache for both users
self._invalidate_partner_cache(user_id)
self._invalidate_partner_cache(partner_id)
```

**Step 5: Run tests to verify they pass**

Run: `cd /Users/ytchou/Project/focus-squad/backend && pytest tests/unit/services/test_partner_service.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add backend/app/services/partner_service.py backend/tests/unit/services/test_partner_service.py
git commit -m "feat(partners): add Redis cache for accepted partner IDs"
```

---

## Task 4: Message Cursor Reset

**Files:**
- Modify: `frontend/src/stores/message-store.ts`
- Test: `frontend/src/stores/__tests__/message-store.test.ts`

**Step 1: Create test file**

Create `frontend/src/stores/__tests__/message-store.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useMessageStore } from "../message-store";

// Mock the API client
vi.mock("@/lib/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: vi.fn(),
}));

import { api } from "@/lib/api/client";

describe("message-store", () => {
  beforeEach(() => {
    // Reset store to initial state
    useMessageStore.setState({
      conversations: [],
      activeConversationId: null,
      messages: {},
      totalUnreadCount: 0,
      isLoadingConversations: false,
      isLoadingMessages: false,
      isSending: false,
      hasMore: {},
      cursors: {},
      error: null,
    });
    vi.clearAllMocks();
  });

  describe("openConversation cursor reset", () => {
    it("should clear previous conversation cursor when switching", async () => {
      // Setup: conversation A has messages and cursor
      useMessageStore.setState({
        activeConversationId: "conv-a",
        messages: { "conv-a": [{ id: "msg-1" }] as any },
        cursors: { "conv-a": "cursor-a" },
        hasMore: { "conv-a": false },
      });

      // Mock API response for new conversation
      vi.mocked(api.get).mockResolvedValueOnce({
        messages: [{ id: "msg-2" }],
        has_more: true,
        next_cursor: "cursor-b",
      });
      vi.mocked(api.put).mockResolvedValueOnce({}); // markRead

      // Act: switch to conversation B
      await useMessageStore.getState().openConversation("conv-b");

      // Assert: conversation A cursor should be reset
      const state = useMessageStore.getState();
      expect(state.cursors["conv-a"]).toBeNull();
      expect(state.hasMore["conv-a"]).toBe(true);

      // Conversation B should have its new cursor
      expect(state.cursors["conv-b"]).toBe("cursor-b");
      expect(state.activeConversationId).toBe("conv-b");
    });

    it("should not reset cursor when opening same conversation", async () => {
      // Setup: already on conversation A
      useMessageStore.setState({
        activeConversationId: "conv-a",
        cursors: { "conv-a": "cursor-a" },
        hasMore: { "conv-a": false },
      });

      // Mock API response
      vi.mocked(api.get).mockResolvedValueOnce({
        messages: [],
        has_more: true,
        next_cursor: "cursor-a-new",
      });
      vi.mocked(api.put).mockResolvedValueOnce({});

      // Act: re-open same conversation
      await useMessageStore.getState().openConversation("conv-a");

      // Assert: cursor should be updated (not set to null first)
      const state = useMessageStore.getState();
      expect(state.cursors["conv-a"]).toBe("cursor-a-new");
    });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ytchou/Project/focus-squad/frontend && npm test -- --run src/stores/__tests__/message-store.test.ts`
Expected: FAIL (cursor reset logic not implemented)

**Step 3: Implement cursor reset in openConversation**

Modify `frontend/src/stores/message-store.ts` - update `openConversation` (around line 110):

```typescript
openConversation: async (id: string) => {
  const prevId = get().activeConversationId;

  // Clear pagination state for previous conversation to ensure fresh data on return
  if (prevId && prevId !== id) {
    set((state) => ({
      cursors: { ...state.cursors, [prevId]: null },
      hasMore: { ...state.hasMore, [prevId]: true },
    }));
  }

  set({ activeConversationId: id, isLoadingMessages: true });

  try {
    const data = await api.get<{
      messages: MessageInfo[];
      has_more: boolean;
      next_cursor: string | null;
    }>(`/api/v1/messages/${id}/messages`);

    set((state) => ({
      messages: { ...state.messages, [id]: data.messages },
      hasMore: { ...state.hasMore, [id]: data.has_more },
      cursors: { ...state.cursors, [id]: data.next_cursor },
      isLoadingMessages: false,
    }));

    await get().markRead(id);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Failed to load messages";
    set({ error: message, isLoadingMessages: false });
  }
},
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/ytchou/Project/focus-squad/frontend && npm test -- --run src/stores/__tests__/message-store.test.ts`
Expected: All tests PASS

**Step 5: Run all frontend tests**

Run: `cd /Users/ytchou/Project/focus-squad/frontend && npm test`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add frontend/src/stores/message-store.ts frontend/src/stores/__tests__/message-store.test.ts
git commit -m "fix(messages): reset cursor when switching conversations"
```

---

## Task 5: Analytics Retention - Database Migration

**Files:**
- Create: `supabase/migrations/032_analytics_retention.sql`

**Step 1: Create the migration file**

```sql
-- Migration: 032_analytics_retention.sql
-- Purpose: RPC for batch deletion of old analytics events

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
    -- Use CTE to select IDs first, then delete
    -- This avoids locking the entire table during deletion
    WITH to_delete AS (
        SELECT id
        FROM session_analytics_events
        WHERE created_at < NOW() - cutoff_interval
        ORDER BY created_at ASC  -- Delete oldest first
        LIMIT batch_limit
        FOR UPDATE SKIP LOCKED  -- Skip locked rows to avoid contention
    )
    DELETE FROM session_analytics_events
    WHERE id IN (SELECT id FROM to_delete);

    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    RETURN json_build_object('deleted', v_deleted);
END;
$$;

COMMENT ON FUNCTION delete_old_analytics IS
'Batch delete analytics events older than cutoff_interval. Uses FOR UPDATE SKIP LOCKED to avoid contention. Returns count of deleted rows.';
```

**Step 2: Commit**

```bash
git add supabase/migrations/032_analytics_retention.sql
git commit -m "feat(db): add batch delete RPC for analytics retention"
```

---

## Task 6: Analytics Retention - Celery Task

**Files:**
- Create: `backend/app/tasks/analytics_tasks.py`
- Modify: `backend/app/core/celery_app.py`
- Test: `backend/tests/unit/tasks/test_analytics_tasks.py`

**Step 1: Write the failing test**

Create `backend/tests/unit/tasks/test_analytics_tasks.py`:

```python
import pytest
from unittest.mock import MagicMock, patch


class TestCleanupOldAnalytics:
    """Tests for analytics cleanup Celery task."""

    @patch("app.tasks.analytics_tasks.get_supabase")
    def test_cleanup_single_batch(self, mock_get_supabase: MagicMock):
        """Should delete all old events in one batch if fewer than batch_size."""
        from app.tasks.analytics_tasks import cleanup_old_analytics

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # First call returns 500 deleted (less than 1000 batch)
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={"deleted": 500}
        )

        result = cleanup_old_analytics()

        assert result == {"deleted": 500}
        mock_supabase.rpc.assert_called_once_with(
            "delete_old_analytics",
            {"cutoff_interval": "1 year", "batch_limit": 1000}
        )

    @patch("app.tasks.analytics_tasks.get_supabase")
    def test_cleanup_multiple_batches(self, mock_get_supabase: MagicMock):
        """Should loop until fewer than batch_size deleted."""
        from app.tasks.analytics_tasks import cleanup_old_analytics

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # First two calls return 1000, third returns 200
        mock_supabase.rpc.return_value.execute.side_effect = [
            MagicMock(data={"deleted": 1000}),
            MagicMock(data={"deleted": 1000}),
            MagicMock(data={"deleted": 200}),
        ]

        result = cleanup_old_analytics()

        assert result == {"deleted": 2200}  # 1000 + 1000 + 200
        assert mock_supabase.rpc.call_count == 3

    @patch("app.tasks.analytics_tasks.get_supabase")
    def test_cleanup_nothing_to_delete(self, mock_get_supabase: MagicMock):
        """Should return 0 when no old events exist."""
        from app.tasks.analytics_tasks import cleanup_old_analytics

        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.rpc.return_value.execute.return_value = MagicMock(
            data={"deleted": 0}
        )

        result = cleanup_old_analytics()

        assert result == {"deleted": 0}
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/ytchou/Project/focus-squad/backend && pytest tests/unit/tasks/test_analytics_tasks.py -v`
Expected: FAIL (module doesn't exist)

**Step 3: Create the Celery task**

Create `backend/app/tasks/analytics_tasks.py`:

```python
"""
Analytics cleanup tasks.

Handles:
- Deleting analytics events older than retention period (1 year)
"""

import logging

from celery import shared_task

from app.core.database import get_supabase

logger = logging.getLogger(__name__)

RETENTION_INTERVAL = "1 year"
BATCH_SIZE = 1000


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def cleanup_old_analytics(self):
    """
    Delete analytics events older than 1 year.

    Uses batch deletion (1000 rows at a time) to avoid lock contention.
    Runs daily at 02:00 UTC via Celery Beat.
    """
    supabase = get_supabase()
    total_deleted = 0

    while True:
        try:
            result = supabase.rpc(
                "delete_old_analytics",
                {"cutoff_interval": RETENTION_INTERVAL, "batch_limit": BATCH_SIZE}
            ).execute()

            deleted_count = result.data.get("deleted", 0) if result.data else 0
            total_deleted += deleted_count

            logger.debug(f"Analytics cleanup batch: deleted {deleted_count} events")

            if deleted_count < BATCH_SIZE:
                break  # No more rows to delete

        except Exception as exc:
            logger.error(f"Analytics cleanup failed after deleting {total_deleted}: {exc}")
            raise self.retry(exc=exc)

    logger.info(f"Analytics cleanup complete: deleted {total_deleted} events older than {RETENTION_INTERVAL}")
    return {"deleted": total_deleted}
```

**Step 4: Add to Celery app includes**

Modify `backend/app/core/celery_app.py` - add to includes list (line 27):

```python
include=[
    "app.tasks.livekit_tasks",
    "app.tasks.credit_tasks",
    "app.tasks.session_tasks",
    "app.tasks.schedule_tasks",
    "app.tasks.rating_tasks",
    "app.tasks.analytics_tasks",  # Add this line
],
```

**Step 5: Add beat schedule**

Add to `beat_schedule` in `backend/app/core/celery_app.py` (after line 65):

```python
"cleanup-old-analytics": {
    "task": "app.tasks.analytics_tasks.cleanup_old_analytics",
    "schedule": crontab(hour=2, minute=0),  # Daily at 02:00 UTC
},
```

**Step 6: Run tests to verify they pass**

Run: `cd /Users/ytchou/Project/focus-squad/backend && pytest tests/unit/tasks/test_analytics_tasks.py -v`
Expected: All tests PASS

**Step 7: Run all backend tests**

Run: `cd /Users/ytchou/Project/focus-squad/backend && pytest`
Expected: All tests PASS

**Step 8: Commit**

```bash
git add backend/app/tasks/analytics_tasks.py backend/app/core/celery_app.py backend/tests/unit/tasks/test_analytics_tasks.py
git commit -m "feat(analytics): add Celery task for 1-year retention cleanup"
```

---

## Task 7: Update TODO.md

**Files:**
- Modify: `TODO.md`

**Step 1: Mark P2 items as complete**

Update the P2 section in TODO.md:

```markdown
### [P2] Medium Priority - Second sprint
- [x] Add analytics retention policy (1-year TTL via Celery)
- [x] Serialize essence purchases (SELECT FOR UPDATE)
- [x] Cache partner lists for RLS performance
- [x] Reset message cursors on conversation switch in message-store

### Test Coverage Gaps
- [x] Add tests for essence purchase race condition
- [x] Add tests for message pagination cursor reset
```

**Step 2: Commit**

```bash
git add TODO.md
git commit -m "docs: mark P2 reliability fixes as complete"
```

---

## Verification Checklist

After completing all tasks, verify:

1. **Database migrations**: Both new migration files exist
   ```bash
   ls supabase/migrations/03*.sql
   ```

2. **Backend tests pass**:
   ```bash
   cd backend && pytest -v
   ```

3. **Frontend tests pass**:
   ```bash
   cd frontend && npm test
   ```

4. **Linting passes**:
   ```bash
   cd backend && ./venv/bin/ruff check . && ./venv/bin/ruff format --check .
   cd frontend && npm run lint
   ```

5. **Type checking passes**:
   ```bash
   cd backend && mypy app/
   ```
