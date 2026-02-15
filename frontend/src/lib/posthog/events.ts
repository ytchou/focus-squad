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
  properties?: Record<string, unknown>
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
  selection?: string
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
  remainingSeconds: number
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
