# Focus Squad - Technical Specification v1.0

## Executive Summary

Focus Squad is a web-based body-doubling platform featuring 4-person virtual study tables with audio-only communication, gamification through collectibles, and a credit-based economy. Optimized for the Taiwan market (cafes/libraries culture).

---

## 1. Core Product Decisions

### Session Structure (55 minutes total)
```
[0-3 min]   Setup/trickle-in (optional, doesn't count for rewards)
[3-28 min]  First work block (25 min)
[28-30 min] Rest break (2 min)
[30-50 min] Second work block (20 min)
[50-55 min] Social/chat period (optional)
```

**Earning Rule:** Complete minutes 3-50 (the 47-min core) = earn 1 Furniture Essence

### Table Matching
- **Fixed time slots:** Tables start at :00 and :30 of each hour
- **Quick match:** One-click "Find Table" with optional filters (topic, quiet mode, language)
- **Minimum 2 to start:** If <4 users after 3-min setup, tables merge
- **AI companions:** Fill remaining empty seats with simulated presence (fake activity indicators, no AI API)

### Disconnect Handling
- **2-minute grace period:** Brief disconnects don't penalize
- **Graceful degradation:** Table continues with remaining users (min 2)
- **No backfill:** Empty seats stay empty (or AI companion) after session starts

---

## 2. User System

### Authentication
- **Google OAuth** (single provider for MVP)
- **Custom username** chosen during onboarding
- **Bilingual:** English + Traditional Chinese from day one

### User Profile ("Home")
- **Stats:** Total focus hours, session count, current streak, reliability badge
- **Collection grid:** Earned furniture/items displayed as cards (no room renderer)
- **Activity history:** Recent sessions (topics, not participants)
- **Social fields:** Optional bio, social links, study interests

### Avatar System
- **Customizable avatar builder:** Mix-and-match components
  - Hair styles (10+)
  - Face shapes (5+)
  - Accessories (glasses, headphones, etc.)
  - Colors/tints
- Displayed during sessions instead of video

---

## 3. Active Status Indicators

Since we're audio-only, presence is shown through:

| Indicator | Data Transmitted | Privacy |
|-----------|------------------|---------|
| Audio waveform | Live audio levels | Always on |
| Keyboard/mouse activity | Binary (active/idle) | **Opt-in only** |
| Self-reported status | Manual toggle | User-controlled |
| Pomodoro position | Current timer phase | Shared by system |

---

## 4. Credit Economy

### Tiers
| Tier | Weekly Credits | Price | Features |
|------|----------------|-------|----------|
| Free | 2 | $0 | Public tables, basic avatar |
| Pro | 8 | TBD | Credit gifting (up to 4/wk) |
| Elite | 12 | TBD | Credit gifting (up to 4/wk), priority matching |
| Infinite | Unlimited | TBD | All skins, no gifting |

### Zero Credits UX
1. Show upgrade modal with pricing
2. Display countdown to weekly refresh
3. Offer referral option: "Refer a friend, both earn 1 credit"

### Referral System
- **Trigger:** Friend completes their first full session
- **Reward:** Mutual - both referrer AND friend get 1 bonus credit

### Streak Bonuses
- 10 consecutive sessions = bonus essence reward
- (Define exact bonus amount during implementation)

**MVP CUT:** Private tables removed from scope

---

## 5. Peer Review & Trust

### Rating Flow
- At session end (during 5-min social period)
- Rate each tablemate: **Green** (present/working) or **Red** (no-show/disruptive)
- **Skip** option: "I wasn't paying attention to them"

### Reliability Score
- **Algorithm:** Weighted average with time decay
- Recent ratings matter more than old ones
- High-reliability users' ratings count more (weighted by reviewer score)

### Penalties
- 3 Red ratings in a rolling week = **48-hour ban + lose 1 credit**
- Public reliability badge visible on profile

---

## 6. Quiet Mode vs Forced Audio

| Mode | Microphone | Chat | Use Case |
|------|------------|------|----------|
| Forced Audio (default) | Required ON | Available | High accountability |
| Quiet Mode | Muted | Primary interaction | Libraries, shared spaces |

- Host selects mode when table is created
- Shared Pomodoro timer visible in both modes

---

## 7. Moderation

### Report System
- "Report User" button with categories:
  - Harassment
  - Inappropriate content
  - No-show/gaming the system
  - Other
- Reports go to manual review queue (email initially)

### Chat Filtering
- Basic keyword blocklist for text chat
- Auto-flag messages with blocked words for review

---

## 8. Notifications

| Event | Email | Browser Push |
|-------|-------|--------------|
| Session starting in 5 min | ✓ | ✓ |
| Matched to a table | | ✓ |
| Weekly credit refresh | ✓ | |
| Received a Red rating | ✓ | |
| Friend joined (if following) | | ✓ |

User preferences panel to configure channels.

---

## 9. Technical Architecture

### Stack
```
Frontend:  Next.js 14 (App Router) + Tailwind CSS + Lucide Icons
Backend:   FastAPI (Python) + Supabase (Postgres) + Redis
Real-time: LiveKit (audio + data channels)
Hosting:   Vercel (frontend) + Railway (backend)
Analytics: Mixpanel or Amplitude (full behavioral tracking)
```

### Real-time Strategy
- **LiveKit data channels** for ALL real-time sync:
  - Timer state
  - Activity indicators
  - Chat messages
  - Presence updates
- Single connection per user (audio + data)

### Database (Supabase)
Key tables:
- `users` - profile, settings, reliability_score
- `sessions` - scheduled tables, participants, mode
- `credits` - balance, transactions, tier
- `ratings` - peer reviews with weights
- `items` - furniture collection
- `referrals` - tracking codes and conversions

### Redis Usage
- Session state cache (who's in which room)
- Rate limiting
- Ephemeral activity data

---

## 10. Payments (Research Required)

**Target:** Taiwan-local payment methods

Options to evaluate:
1. **ECPay** - Popular in Taiwan, supports credit cards + convenience store
2. **LINE Pay** - High penetration in Taiwan market
3. **NewebPay** - Local gateway, good coverage
4. **Recur** - Subscription management focus

**Research deliverable:** Compare integration complexity, fees, subscription support

---

## 11. Design System

### Aesthetic
- **Lo-fi cozy** - warm, inviting, calming
- Earth tones + warm accents
- Minimalist UI, avoid dense text
- Soft shadows, rounded corners

### Color Palette
```
Background:  #FAF7F2 (warm off-white)
Surface:     #F5EFE6 (cream)
Primary:     #8B7355 (coffee brown)
Accent:      #D4A574 (warm tan)
Text:        #3D3D3D (soft black)
Success:     #7D9B76 (muted sage)
Warning:     #C9A962 (muted gold)
Error:       #B85C5C (muted red)
```

### Typography
- Clean sans-serif (Inter or similar)
- Large touch targets for mobile
- Scannable, scroller-friendly layouts

---

## 12. PWA Requirements

- Service worker for offline shell
- Web app manifest for installation
- Push notification support (Web Push API)
- Responsive design (mobile-first within laptop-optimized bounds)

---

## 13. Testing Strategy

**Coverage target:** ~20% (critical paths only)

### Must-test areas:
- Credit calculation and transactions
- Table matching logic
- Reliability score computation
- Rating weight calculations
- Session state transitions

### Deferred:
- E2E UI tests
- Integration tests for LiveKit
- Load testing

---

## 14. Analytics Events (Behavioral)

### Core Events
- `session_joined` - user enters a table
- `session_completed` - user finishes full session
- `session_abandoned` - user leaves early
- `credit_spent` - credit consumed
- `credit_earned` - referral/bonus credit
- `rating_submitted` - peer review given
- `upgrade_viewed` - pricing modal shown
- `upgrade_completed` - payment successful

### Funnel Events
- `signup_started` → `signup_completed`
- `matching_started` → `matching_completed` / `matching_abandoned`
- `onboarding_step_1` → `onboarding_completed`

---

## 15. Compliance TODO

**Action required:** Research Taiwan PDPA requirements
- Data localization requirements?
- Consent mechanisms needed?
- Privacy policy requirements?
- Supabase region selection (Singapore closest?)

---

## 16. Phase 1 MVP Scope

### In Scope
- [x] Google OAuth + custom username
- [x] Quick match + filters (topic, quiet mode)
- [x] Fixed time slot tables (:00, :30)
- [x] 4-person audio rooms via LiveKit
- [x] Shared Pomodoro timer (55-min structure)
- [x] Active status indicators (audio, opt-in keyboard, manual)
- [x] AI companions for empty seats (simulated presence)
- [x] Customizable avatar builder
- [x] Free tier (2 credits/week)
- [x] Peer review (Green/Red/Skip)
- [x] Reliability score with decay
- [x] Profile with collection grid
- [x] Text chat (with keyword filter)
- [x] Bilingual UI (EN + zh-TW)
- [x] Email + browser push notifications
- [x] Full behavioral analytics

### Deferred to Phase 2
- [ ] Video mode
- [ ] Private tables
- [ ] AI task breakdown (Claude API)
- [ ] 2D/3D room renderer
- [ ] Advanced moderation dashboard
- [ ] Multiple social login providers
- [ ] Native mobile apps

---

## 17. Open Questions

1. **Furniture essence amounts:** How much per session? How much for streak bonus?
2. **Payment pricing:** What should Pro/Elite/Infinite cost?
3. **Avatar assets:** Commission artist or use asset library?
4. **Keyword blocklist:** Source or create custom list?
5. **AI companion names:** Pre-defined or generated?

---

## 18. Success Criteria (Alpha)

- 50+ unique users complete at least 1 session
- 30%+ D7 retention (return within 7 days)
- Average session completion rate > 80%
- Peer review participation > 90%
- < 5% Red rating rate

---

## 19. Implementation Order (Suggested)

### Week 1-2: Foundation
1. Project setup (Next.js + FastAPI + Supabase)
2. Google OAuth flow
3. Basic user profile CRUD
4. Database schema

### Week 3-4: Core Loop
5. LiveKit integration (audio rooms)
6. Table matching logic
7. Session state machine (timer phases)
8. Credit system

### Week 5-6: Social & Polish
9. Peer review system
10. Chat with filtering
11. Avatar builder
12. Profile collection view

### Week 7-8: Launch Prep
13. Notifications (email + push)
14. Analytics instrumentation
15. i18n (zh-TW)
16. Payment integration research/implementation

---

*Spec version: 1.0*
*Last updated: 2026-01-27*
*Status: Approved*
