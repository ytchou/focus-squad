# Focus Squad - Context Anchor

## What Is This?
Body-doubling platform with 4-person audio study tables, credit economy, and collectibles. Taiwan market focus.

## Tech Stack
| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14 (App Router), Tailwind CSS, Lucide Icons, Zustand |
| Backend | FastAPI (Python 3.9+), Pydantic |
| Database | Supabase (PostgreSQL) |
| Cache | Redis |
| Real-time | LiveKit (audio + data channels) |
| Auth | Google OAuth via NextAuth |
| i18n | next-intl (EN + zh-TW) |
| Hosting | Vercel (frontend) + Railway (backend) |

## Project Structure
```
focus-squad/
├── frontend/           # Next.js 14
│   └── src/app/        # App Router pages
├── backend/            # FastAPI
│   ├── app/routers/    # API endpoints
│   ├── app/services/   # Business logic
│   ├── app/models/     # Pydantic models
│   ├── app/core/       # Config, database
│   └── venv/           # Python virtual env
├── supabase/migrations/  # SQL schema
├── PRD.md              # Product requirements
└── SPEC.md             # Full technical spec
```

## Commands

### Frontend
```bash
cd frontend
npm install && npm run dev     # Dev server :3000
npm run build                  # Production build
npm run lint                   # ESLint
```

### Backend
```bash
cd backend
source venv/bin/activate       # Activate venv
pip install -r requirements.txt
uvicorn main:app --reload      # Dev server :8000
pytest                         # Run tests
mypy .                         # Type check
```

## Critical Business Rules

### Session Structure (55 min)
```
[0-3]   Setup (doesn't count)
[3-28]  Work block 1 (25 min)
[28-30] Break (2 min)
[30-50] Work block 2 (20 min)
[50-55] Social (optional)
```
- Tables start at :00 and :30 each hour
- Min 2 users to start; AI companions fill empty seats
- Complete minutes 3-50 → earn 1 Furniture Essence

### Credit System
| Tier | Weekly | Gift Limit |
|------|--------|------------|
| Free | 2 | - |
| Pro | 8 | 4/wk |
| Elite | 12 | 4/wk |
| Infinite | ∞ | - |

### Peer Review & Trust
- Rate tablemates: **Green** / **Red** / **Skip**
- 3 Reds in rolling week → 48hr ban + lose 1 credit
- Reliability score: weighted average with time decay

### Table Modes
- **Forced Audio** (default): Mic required ON
- **Quiet Mode**: Mic muted, chat-only

## Design System

### Colors
```css
--background: #FAF7F2;  /* warm off-white */
--surface: #F5EFE6;     /* cream */
--primary: #8B7355;     /* coffee brown */
--accent: #D4A574;      /* warm tan */
--text: #3D3D3D;        /* soft black */
--success: #7D9B76;     /* muted sage */
--warning: #C9A962;     /* muted gold */
--error: #B85C5C;       /* muted red */
```

### Aesthetic
- Lo-fi cozy, earth tones, minimalist
- Soft shadows, rounded corners
- Inter font, large touch targets

## Coding Standards

### TypeScript (Frontend)
- Strict mode enabled
- Functional components with hooks
- Tailwind for all styling (no CSS files)
- Zustand for client state

### Python (Backend)
- Type hints on all functions
- Use `Optional[X]` not `X | None` (Python 3.9 compat)
- Pydantic for validation
- FastAPI dependency injection

### General
- No emojis in code unless requested
- Minimal comments (self-documenting code)
- Test critical paths: credits, matching, ratings

## CTO Role Instructions
- Push back when necessary; don't be a people pleaser
- Ask clarifying questions instead of guessing
- High-level plans first, then concrete steps
- Show minimal diffs, not entire files
- Suggest tests and rollback plans for risky changes

## Key Files Reference
- Database schema: `supabase/migrations/001_initial_schema.sql`
- API routes: `backend/app/routers/`
- Full spec: `SPEC.md`
