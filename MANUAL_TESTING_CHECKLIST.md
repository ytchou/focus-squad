# Manual Testing Checklist - Session UX & Analytics

## Prerequisites

1. **Start Backend:**
   ```bash
   cd backend
   source venv/bin/activate
   uvicorn main:app --reload
   ```

2. **Start Frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Run Migration:**
   ```bash
   supabase db push
   ```

---

## Test 1: Immediate Session (<1 minute)

**Goal:** Verify immediate session flow (session starting within 60 seconds)

**Steps:**
1. Wait until system clock shows :29 or :59 (e.g., 2:29 PM or 2:59 PM)
2. Click "Join a Table" on dashboard
3. **Expected:**
   - Redirect to waiting room immediately
   - Countdown shows <60 seconds
   - "Get Ready!" message appears at T-10 seconds
   - Auto-redirect to session page at T-0

**Analytics Verification:**
```sql
SELECT * FROM session_analytics_events
WHERE event_type = 'waiting_room_entered'
ORDER BY created_at DESC LIMIT 1;

-- Check metadata.is_immediate should be true
-- Check metadata.wait_minutes should be 0
```

---

## Test 2: Future Session with Page Reload

**Goal:** Verify localStorage persistence and auto-redirect after reload

**Steps:**
1. Click "Join a Table" at 2:15 PM (for 2:30 PM session)
2. **Expected:** Waiting room shows 15:00 countdown
3. Close browser tab completely
4. Reopen browser and navigate to dashboard
5. **Expected:**
   - Auto-redirect to waiting room
   - Countdown continues from current time
6. Wait until T-10 seconds
7. **Expected:** "Get Ready!" message appears with pulse animation
8. Wait until T-0
9. **Expected:** Auto-redirect to active session page

**Analytics Verification:**
```sql
SELECT event_type, metadata, created_at
FROM session_analytics_events
WHERE session_id = '<your-session-id>'
ORDER BY created_at;

-- Should see:
-- 1. waiting_room_entered (from quick-match)
-- 2. waiting_room_resumed (after page reload)
-- 3. session_joined_from_waiting_room (at T-0)
```

---

## Test 3: Leave Early (No Refund)

**Goal:** Verify no-refund policy and analytics tracking

**Steps:**
1. Join a table (any time)
2. Enter waiting room
3. Click "Leave Session (No Refund)" button
4. **Expected:**
   - Button shows "Leaving..." (disabled state)
   - Redirect to dashboard
5. Check credit balance
6. **Expected:** Credit NOT refunded (balance remains the same)

**Database Verification:**
```sql
-- Check credit transactions
SELECT * FROM credit_transactions
WHERE user_id = '<your-user-id>'
ORDER BY created_at DESC LIMIT 2;

-- Should see only 1 deduction, NO refund transaction

-- Check analytics
SELECT * FROM session_analytics_events
WHERE event_type = 'waiting_room_abandoned'
ORDER BY created_at DESC LIMIT 1;

-- Should show metadata.reason = 'user_clicked_leave'
```

---

## Test 4: No-Show Scenario (No Refund)

**Goal:** Verify credit not refunded for no-shows

**Steps:**
1. Join a table at 2:15 PM (for 2:30 PM session)
2. Enter waiting room
3. Close browser completely (don't return)
4. Wait until after 2:30 PM
5. Reopen browser, check credit balance
6. **Expected:** Credit still deducted (no refund)

**Database Verification:**
```sql
-- Check participant status
SELECT * FROM session_participants
WHERE user_id = '<your-user-id>'
AND session_id = '<your-session-id>';

-- joined_at should be NULL (never joined active session)
-- left_at should be NULL or set if they left early

-- Check analytics
SELECT * FROM session_analytics_events
WHERE session_id = '<your-session-id>'
ORDER BY created_at;

-- Should only show 'waiting_room_entered'
-- NO 'session_joined_from_waiting_room' event
```

---

## Test 5: Edge Cases - Time Slots

**Goal:** Verify 3-minute minimum threshold

**Test 5a: Join at :28**
1. Wait until :28 (e.g., 2:28 PM)
2. Click "Join a Table"
3. **Expected:** Matched to NEXT :30 slot (3:00 PM, not 2:30 PM)
4. **Rationale:** Less than 3 minutes until 2:30, so skip to next slot

**Test 5b: Join at :58**
1. Wait until :58 (e.g., 2:58 PM)
2. Click "Join a Table"
3. **Expected:** Matched to NEXT :00 slot (3:30 PM, not 3:00 PM)

---

## Test 6: Multiple Tabs Open

**Goal:** Verify state synchronization across tabs

**Steps:**
1. Open dashboard in Tab 1
2. Open dashboard in Tab 2
3. In Tab 1, click "Join a Table"
4. **Expected (Tab 1):** Redirect to waiting room
5. Switch to Tab 2
6. Refresh Tab 2
7. **Expected (Tab 2):** Auto-redirect to waiting room (same session)

---

## Test 7: Audio Privacy Warning

**Goal:** Verify user sees privacy notice

**Steps:**
1. Join any table, enter waiting room
2. **Expected:**
   - Notice: "Audio will connect automatically"
   - Warning: "Your microphone will be unmuted when the session begins"
   - Info: "No refunds for early departure"

---

## Test 8: Zero Credits Edge Case

**Goal:** Verify button disabled when no credits

**Steps:**
1. Use dev tools to set credits to 0 (or exhaust credits)
2. Refresh dashboard
3. **Expected:**
   - "Join a Table" button is disabled (grayed out)
   - Shows "No credits available" subtitle
   - Button cannot be clicked

---

## Test 9: Toast Notifications

**Goal:** Verify user feedback on success/error

**Test 9a: Success Toast**
1. Click "Join a Table"
2. **Expected:**
   - Green toast: "Match found!"
   - Description shows wait time or "Session starting now!"

**Test 9b: Error Toast (Simulate)**
1. Stop backend server
2. Click "Join a Table"
3. **Expected:**
   - Red toast: "Failed to join table"
   - Description: "Please try again"

---

## Analytics Queries for Post-Testing

**No-Show Rate:**
```sql
SELECT
  COUNT(*) FILTER (WHERE event_type = 'waiting_room_entered') AS total_matches,
  COUNT(*) FILTER (WHERE event_type = 'session_joined_from_waiting_room') AS showed_up,
  COUNT(*) FILTER (WHERE event_type = 'waiting_room_abandoned') AS abandoned,
  (COUNT(*) FILTER (WHERE event_type = 'waiting_room_entered') -
   COUNT(*) FILTER (WHERE event_type = 'session_joined_from_waiting_room')) AS no_shows
FROM session_analytics_events
WHERE created_at > NOW() - INTERVAL '1 hour';
```

**Abandonment Reasons:**
```sql
SELECT
  metadata->>'reason' AS reason,
  COUNT(*) AS count
FROM session_analytics_events
WHERE event_type = 'waiting_room_abandoned'
  AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY metadata->>'reason';
```

---

## Success Criteria

✅ All immediate sessions (<1 min) show correct countdown and auto-redirect
✅ Page reload preserves state and resumes waiting room
✅ Leave early does NOT refund credit
✅ No-shows do NOT get refunded
✅ Time slot edge cases (:28, :58) work correctly
✅ Multiple tabs sync via localStorage
✅ Privacy warnings visible and clear
✅ Zero credits disables button
✅ Toast notifications provide feedback
✅ Analytics events logged correctly

---

## Troubleshooting

**Issue: Analytics events not logging**
- Check backend logs for errors
- Verify `session_analytics_events` table exists
- Check API endpoint `/api/v1/analytics/track` is registered

**Issue: Waiting room not persisting on reload**
- Check browser localStorage (key: `focus-squad-session`)
- Verify Zustand persist middleware is configured
- Check console for errors

**Issue: Countdown timer not working**
- Check system time is accurate
- Verify `sessionStartTime` is in UTC
- Check browser console for JavaScript errors
