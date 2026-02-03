# CLAUDE.MD - Context Anchor

## What You're Building
**Focus Squad** is a body-doubling platform with 4-person audio study tables, credit economy, and collectibles. Taiwan market focus.

**For complete product specifications:** See [SPEC.md](SPEC.md) and [PRD.md](PRD.md)

## Tech Stack Quick Reference
- **Frontend:** Next.js 14 (App Router), Tailwind CSS, Lucide Icons, Zustand
- **Backend:** FastAPI (Python 3.9+), Pydantic
- **Database:** Supabase (PostgreSQL), Redis
- **Real-time:** LiveKit (audio + data channels)
- **Auth:** Google OAuth via NextAuth
- **i18n:** next-intl (EN + zh-TW)
- **Hosting:** Vercel (frontend) + Railway (backend)

**Full technical architecture:** [SPEC.md § Technical Architecture](SPEC.md#9-technical-architecture)

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
├── output/lessons/     # AI session learnings (YYYY-MM-DD dated)
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

### Database Migrations (Supabase)
```bash
supabase migration list --linked  # Check state BEFORE pushing
supabase db push                   # Push migrations to remote
```

**See [ERROR_PREVENTION.md](ERROR_PREVENTION.md)** for common migration errors and fixes

## Critical Business Logic Quick Reference
> **For complete specifications:** [SPEC.md](SPEC.md)

**Quick Reference:**
- **Session Timing:** 55-min structure (3-min setup → 25-min work → 2-min break → 20-min work → 5-min social)
- **Earning Rule:** Complete minutes 3-50 = earn 1 Furniture Essence
- **Credit Tiers:** Free (2/wk), Pro (8/wk), Elite (12/wk), Infinite (∞)
- **Peer Review:** Rate tablemates Green/Red/Skip; 3 Reds in rolling week = 48hr ban + lose 1 credit
- **Table Start Times:** :00 and :30 each hour
- **Min Participants:** 2 users to start; AI companions fill empty seats

**See SPEC.md for detailed information on:**
- Complete session structure and phase timing → [§ Session Structure](SPEC.md#1-core-product-decisions)
- Credit system algorithms and tier features → [§ Credit Economy](SPEC.md#4-credit-economy)
- Peer review scoring and reliability algorithms → [§ Peer Review & Trust](SPEC.md#5-peer-review--trust)
- Design system colors and aesthetic → [§ Design System](SPEC.md#11-design-system)
- Table modes (Forced Audio vs Quiet Mode) → [§ Quiet Mode vs Forced Audio](SPEC.md#6-quiet-mode-vs-forced-audio)

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

### Database (PostgreSQL/Supabase)
- Use `gen_random_uuid()` for UUIDs (not `uuid_generate_v4()`)
- Prefer built-in functions over extensions
- Always check migration state before pushing (`supabase migration list --linked`)
- Use RLS policies to enforce data access at database level
- Add indexes for frequently queried columns (auth_id, user_id, timestamps)

## Testing Standards (Test-Driven Development)

### Philosophy
- **Test-first for critical paths**: Credits, matching, ratings, session state, authentication
- **Test-after for UI/simple features**: Components, utilities
- **Minimum coverage**: ~20% overall, 80%+ for critical business logic

### TDD Enforcement Rules (MANDATORY)
1. **Before implementing critical business logic**: Write failing tests first
2. **Before merging any PR**: All tests must pass
3. **When modifying existing code**: Add tests for uncovered edge cases
4. **When fixing bugs**: Write a regression test that fails before fix, passes after
5. **Coverage gates**:
   - Critical paths (auth, credits, sessions, ratings): 80%+ required
   - Services: 70%+ recommended
   - Overall codebase: 20%+ minimum

### Critical Paths Requiring Tests
These areas MUST have tests before implementation:
- `backend/app/core/auth.py` - JWT validation, user context
- `backend/app/core/middleware.py` - Request authentication
- `backend/app/services/credit_service.py` - Credit transactions
- `backend/app/services/session_service.py` - Session matching
- `backend/app/services/rating_service.py` - Peer review scoring
- `frontend/src/stores/` - State management stores

### Frontend Testing (Vitest)
```bash
npm run test              # Run all tests
npm run test:watch        # Watch mode for development
npm run test:coverage     # Coverage report
```

**Test File Structure**:
```
frontend/src/
  components/
    Button.tsx
    __tests__/
      Button.test.tsx
```

**Example Test**:
```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import Button from '../Button';

describe('Button', () => {
  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click</Button>);
    fireEvent.click(screen.getByText('Click'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
```

### Backend Testing (pytest)
```bash
pytest                    # Run all tests
pytest --cov=app          # With coverage
pytest -m unit            # Unit tests only
```

**Test File Structure**:
```
backend/tests/
  unit/
    services/
      test_credit_service.py
  integration/
    routers/
      test_credits.py
  conftest.py  # Shared fixtures
```

**Example Test**:
```python
import pytest
from app.services.credit_service import CreditService

@pytest.mark.unit
async def test_credit_deduction():
    """Test credit deduction logic."""
    service = CreditService()
    result = await service.deduct_credit(user_id="123", amount=1)
    assert result.success is True
```

### What MUST Be Tested (Pre-Implementation)
1. **Credit System**: Transactions, weekly refresh, tier limits, gifting
2. **Session Matching**: Table creation, time slots, AI companion filling
3. **Peer Review**: Reliability score calculation, 3-Red penalty
4. **Authentication**: JWT validation, user context injection

### CI/CD Requirements
- All PRs run linting, formatting, type checking automatically
- Tests run on every PR (initially optional, will become required post-MVP)
- Secret scanning prevents accidental credential commits
- Branch protection enforces passing checks before merge

## CTO Role Instructions
- Push back when necessary; don't be a people pleaser
- Ask clarifying questions instead of guessing (for ambiguous requirements)
- High-level plans first, then concrete steps
- Show minimal diffs, not entire files
- Suggest tests and rollback plans for risky changes
- **Always mark completed tasks in TODO.md** as work progresses
- **Document errors in ERROR_PREVENTION.md** - When encountering and fixing an error, add it to ERROR_PREVENTION.md with symptom, cause, and prevention strategy

## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Write detailed specs upfront to reduce ambiguity
- **Every plan MUST include a "Verification" section** with specific validation steps (tests to run, commands to execute, expected outputs)
- **Run ALL verification steps** after implementation completes - no exceptions
- **Fix failures immediately** - if any validation fails, fix the issue before marking the task complete

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: create `output/lessons/[lesson-summary-YYYY-MM-DD].md`
- If error-related and preventable: ALSO add to `ERROR_PREVENTION.md`
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing (Context-Dependent)
- **Auto-fix**: When error logs, failing tests, or clear diagnostics are provided - just fix it
- **Ask first**: When requirements are ambiguous or architectural decisions needed
- Point at logs, errors, failing tests - then resolve them
- Go fix failing CI tests without being told how

### 9. Pre-Authorized Actions (No Permission Needed)
- `git checkout` and `git commit` - branch switching and committing allowed freely
- `WebFetch` - fetching web content for research allowed without asking

### 7. Task Management
1. **Plan First**: Write plan to `TODO.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `TODO.md`
6. **Capture Lessons**: Create `output/lessons/[lesson-summary-YYYY-MM-DD].md` after corrections

### 8. Core Principles
- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

## Document Navigation

### Project Documentation
- **[PRD.md](PRD.md)** - Product requirements and vision
- **[SPEC.md](SPEC.md)** - Complete technical specification, business rules, design system
- **[TODO.md](TODO.md)** - Development task tracking and progress
- **[ERROR_PREVENTION.md](ERROR_PREVENTION.md)** - Known errors, symptoms, and solutions
- **[output/lessons/](output/lessons/)** - AI session learnings and corrections (dated files)

### Key Code Files
- **Database schema:** `supabase/migrations/001_initial_schema.sql`
- **API routes:** `backend/app/routers/`
- **Business logic:** `backend/app/services/`
- **Frontend pages:** `frontend/src/app/`

## 🛡️ Security & Privacy Guardrails
Strict Rules for AI Operations:

- Zero-Secrets Policy: NEVER read, edit, or commit .env files or any file containing API keys/tokens. If you encounter a string that looks like a secret, STOP and notify the user immediately.

- Git Safety: Refuse to perform git push or git commit if the changes include hardcoded credentials. Always run a local secret scan before proposing a commit.

- **Automated Secret Scanning**: TruffleHog runs on every push and PR to detect accidental credential commits. If secrets are detected, the build fails immediately. Review `.github/workflows/security.yml` for configuration.

- Local-Only Context: Use the file PRIVATE_CONTEXT.md for sensitive business logic or "secret sauce" prompts. This file is listed in .gitignore and should be read by Claude only when explicitly requested.

- Redaction: When outputting logs or stack traces to the terminal, automatically redact JWTs, passwords, and tokens.

- Path Isolation: Respect all entries in .claudeignore and never attempt to access files in parent directories or sensitive system paths (e.g., ~/.ssh, ~/.aws).