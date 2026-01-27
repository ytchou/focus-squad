# Product Requirements Document (PRD): Focus Squad

## 1. Executive Summary

**Focus Squad** is a web-based productivity platform that utilizes "body doubling" and gamification to help users focus. Unlike 1-on-1 clones, it features **4-person virtual tables** designed for the public-space culture of Taiwan (cafes/libraries), incorporating a credit-based economy and a collectible "Home" system.

**Key Differentiators:**
- Audio-only (no video anxiety) with visual presence indicators
- Fixed time slots for predictable scheduling
- AI companions fill empty seats for consistent 4-person energy
- Bilingual (English + Traditional Chinese) from day one

---

## 2. Target Audience & Problem Statement

* **Target:** Taiwanese university students (exam prep) and remote freelancers (25-35) who work in third spaces.
* **The Problem:** Home environments are distracting; cafes offer companionship but zero accountability; current 1-on-1 tools (Focusmate) are socially exhausting for the local culture.

---

## 3. Core Features & Functional Requirements

### A. The 4-Person Study Table

* **Table Modes:**
  * **Forced Audio (Default):** Microphones remain on for high-intensity accountability.
  * **Quiet Mode:** Interaction is strictly via text chat and UI prompts (ideal for libraries).

* **Audio Infrastructure:** LiveKit for low-latency audio + data channels (no video in MVP).

* **Session Structure (55 minutes total):**
  ```
  [0-3 min]   Setup/trickle-in (optional)
  [3-28 min]  First work block (25 min)
  [28-30 min] Rest break (2 min)
  [30-50 min] Second work block (20 min)
  [50-55 min] Social/chat period (optional)
  ```

* **Table Matching:**
  * Fixed time slots: Tables start at :00 and :30 of each hour
  * Quick match with optional filters (topic, quiet mode, language)
  * Minimum 2 users to start; tables merge if needed
  * AI companions fill remaining empty seats (simulated presence)

* **Active Status Indicators:**
  * Audio waveform (always on)
  * Keyboard/mouse activity (opt-in, binary only)
  * Self-reported status (manual toggle)
  * Shared Pomodoro timer position

### B. Credit-Based Economy (Monetization)

| Tier | Weekly Credits | Price | Features |
| --- | --- | --- | --- |
| **Free** | 2 | $0 | Public tables, basic avatar |
| **Pro** | 8 | TBD | Credit gifting (up to 4/wk) |
| **Elite** | 12 | TBD | Credit gifting (up to 4/wk), priority matching |
| **Infinite** | Unlimited | TBD | All skins, no gifting |

* **Zero Credits UX:** Upgrade modal + weekly reset countdown + referral option
* **Referral:** Both referrer and friend earn 1 credit when friend completes first session

### C. Gamification: The "Home" System

* **Earning:** Complete minutes 3-50 of a session = earn 1 Furniture Essence
* **Streak Bonus:** 10 consecutive sessions = bonus essence reward
* **Collection:** Profile displays earned furniture/items as a card grid (no room renderer in MVP)
* **Visitation:** During 5-min social period, tablemates can view each other's profiles and collections

### D. Avatar System

* **Customizable avatar builder:** Mix-and-match components
  * Hair styles (10+)
  * Face shapes (5+)
  * Accessories (glasses, headphones, etc.)
  * Colors/tints
* Displayed during sessions instead of video

---

## 4. Trust & Accountability (Anti-Cheat)

* **Peer Review:** At the end of every session, users rate their tablemates:
  * **Green:** Present and working
  * **Red:** No-show or disruptive
  * **Skip:** "I wasn't paying attention to them"

* **Reliability Score:**
  * Weighted average with time decay (recent ratings matter more)
  * High-reliability users' ratings count more
  * Publicly visible badge on profile

* **Penalty:** 3 Red ratings in a rolling week = 48-hour ban + loss of 1 credit

---

## 5. Technical Requirements & Stack

* **Frontend:** Next.js 14 (App Router), Tailwind CSS, Lucide Icons
* **Backend:** FastAPI (Python) for logic and credit management
* **Database:** Supabase (PostgreSQL)
* **Real-time:** LiveKit (audio + data channels for all sync)
* **State Cache:** Redis for session state, rate limiting, ephemeral data
* **Hosting:** Vercel (frontend) + Railway (backend)
* **Analytics:** Mixpanel or Amplitude (full behavioral tracking)
* **Payments:** Taiwan-local (ECPay, LINE Pay, NewebPay, or Recur - TBD)

---

## 6. User Experience (Cozy Lo-fi Aesthetic)

* **Visuals:** Earth tones + warm accents, minimalist UI, soft shadows, rounded corners
* **Color Palette:**
  * Background: #FAF7F2 (warm off-white)
  * Surface: #F5EFE6 (cream)
  * Primary: #8B7355 (coffee brown)
  * Accent: #D4A574 (warm tan)
* **Typography:** Clean sans-serif (Inter), large touch targets, scannable layouts
* **PWA:** Service worker, web manifest, push notifications, responsive design

---

## 7. Notifications

| Event | Email | Browser Push |
|-------|-------|--------------|
| Session starting in 5 min | ✓ | ✓ |
| Matched to a table | | ✓ |
| Weekly credit refresh | ✓ | |
| Received a Red rating | ✓ | |

User preferences panel to configure notification channels.

---

## 8. Moderation

* **Report System:** Button with categories (Harassment, Inappropriate content, No-show, Other)
* **Chat Filtering:** Basic keyword blocklist, auto-flag for review
* **Manual Review:** Reports go to email queue initially

---

## 9. MVP Scope

### In Scope (Phase 1)
- Google OAuth + custom username
- Quick match + filters (topic, quiet mode)
- Fixed time slot tables (:00, :30)
- 4-person audio rooms via LiveKit
- Shared Pomodoro timer (55-min structure)
- Active status indicators
- AI companions for empty seats
- Customizable avatar builder
- Free tier (2 credits/week)
- Peer review system
- Reliability score with decay
- Profile with collection grid
- Text chat with keyword filter
- Bilingual UI (EN + zh-TW)
- Email + browser push notifications
- Full behavioral analytics

### Deferred (Phase 2)
- Video mode
- Private tables
- AI task breakdown (Claude API)
- 2D/3D room renderer
- Advanced moderation dashboard
- Multiple social login providers
- Native mobile apps

---

## 10. GTM & Beta Roadmap

1. **Phase 1 (Alpha):** Internal testing with 10 power users (Discord-based)
2. **Phase 2 (Beta):** Invitation-only rollout to 100 Taiwanese "Study-gram" influencers
3. **Phase 3 (Soft Launch):** Open Free tier to public with referral program

---

## 11. Success Metrics (KPIs)

* **Stickiness:** 30%+ D7 retention (return within 7 days)
* **Completion:** >80% session completion rate
* **Trust:** >90% peer review participation, <5% Red rating rate
* **Growth:** 50+ unique users complete at least 1 session in alpha

---

*Last updated: 2026-01-27*
*Status: Approved*
