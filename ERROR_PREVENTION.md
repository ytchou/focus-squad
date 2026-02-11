# Error Prevention Guide

> Living document of errors encountered and prevention strategies
> Updated as we learn from mistakes

---

## Database Migrations (Supabase)

### Error: Migration State Mismatch
**Symptom:** `ERROR: type "user_tier" already exists` when pushing migrations

**Root Cause:** Migration already applied to remote database, but Supabase CLI doesn't know it

**Prevention:**
```bash
# ALWAYS check migration state before pushing
supabase migration list --linked

# If you see mismatches, repair before pushing
supabase migration repair --status applied <migration_number>
```

**When this happens:**
- After manually running SQL in Supabase dashboard
- After restoring a database backup
- When switching between local and remote development
- When joining a project with existing database

---

### Error: UUID Function Not Found
**Symptom:** `ERROR: function uuid_generate_v4() does not exist`

**Root Cause:** `uuid_generate_v4()` requires uuid-ossp extension, which has schema/path issues

**Prevention:**
```sql
-- ❌ DON'T USE (requires extension)
id UUID PRIMARY KEY DEFAULT uuid_generate_v4()

-- ✅ USE INSTEAD (PostgreSQL 13+ built-in)
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

**Why:** Built-in functions have no external dependencies, better portability, guaranteed to work

---

## Python/Ruff Linting

### Error: Deprecated typing imports (UP035/UP006)
**Symptom:** Ruff lint errors like:
- `UP035: typing.Dict is deprecated, use dict instead`
- `UP035: typing.List is deprecated, use list instead`
- `UP006: Use dict instead of Dict for type annotation`

**Root Cause:** Python 3.9+ supports using built-in types (`dict`, `list`, `tuple`) directly in type annotations (PEP 585). The `typing.Dict`, `typing.List`, `typing.Tuple` are now deprecated.

**Prevention:**
```python
# ❌ DON'T USE (deprecated in Python 3.9+)
from typing import Dict, List, Tuple
def process(data: Dict[str, Any]) -> List[str]: ...
def get_pair() -> Tuple[str, int]: ...

# ✅ USE INSTEAD (built-in generics)
from typing import Any, Optional  # Only import what you actually need
def process(data: dict[str, Any]) -> list[str]: ...
def get_pair() -> tuple[str, int]: ...
```

**Quick Fix:**
```bash
# Auto-fix with ruff (requires --unsafe-fixes for type annotation changes)
ruff check --fix --unsafe-fixes .
ruff format .
```

**When this happens:**
- Writing new Python code with type hints
- Copying code from older Python tutorials/examples
- IDE auto-importing from `typing` instead of built-ins

**IDE Configuration:** Configure your IDE to prefer built-in types for auto-imports when targeting Python 3.9+

---

### Error: Unsorted imports (I001)
**Symptom:** `I001: Import block is un-sorted or un-formatted`

**Root Cause:** Ruff enforces isort-style import ordering

**Prevention:**
```bash
# Run ruff format before committing
ruff check --fix .  # Fixes import sorting
ruff format .       # Fixes formatting
```

**Import Order (enforced by ruff):**
1. Standard library imports
2. Third-party imports
3. Local application imports

---

## General Patterns

### When encountering a new error:
1. **Understand** the root cause (don't just fix symptoms)
2. **Document** here with symptom, cause, and prevention
3. **Update** CLAUDE.md if it affects coding standards or commands
4. **Mark** TODO.md task complete

### When updating this file:
- Add date and context for each error
- Include code examples (before/after)
- Link to relevant PRs or commits if available
- Keep entries concise but actionable

---

## Template for New Entries

```markdown
### Error: [Error Name/Description]
**Symptom:** [Error message or behavior]

**Root Cause:** [Why it happened]

**Prevention:**
[Code snippet or commands to avoid this]

**When this happens:**
- [Scenario 1]
- [Scenario 2]

---
```

---

### Error: Schema-Code Mismatch After Migration
**Symptom:** `postgrest.exceptions.APIError: {'message': 'column X does not exist', 'code': '42703'}`

**Root Cause:** A database migration dropped or renamed columns, but application code still references the old column names.

**Example:** Migration `005_credit_system_redesign.sql` dropped `credits_used_this_week` and `week_start_date`, but `user_service.py` still queried:
```python
# ❌ Old code (broken after migration)
.select("credits_remaining, credits_used_this_week, tier, week_start_date")

# ✅ Fixed code (matches new schema)
.select("credits_remaining, tier, credit_cycle_start")
```

**Prevention:**
```bash
# BEFORE pushing a migration that drops/renames columns:
# 1. Search for ALL references to the affected columns
grep -r "column_name" backend/
grep -r "column_name" frontend/

# 2. Update ALL code references BEFORE or WITH the migration
# 3. Test locally with the migration applied
# 4. Run backend tests to catch query errors
pytest backend/tests/
```

**Checklist for DROP COLUMN migrations:**
- [ ] Grep codebase for the column name
- [ ] Update all services that query the column
- [ ] Update all Pydantic models that map the column
- [ ] Update frontend if it displays the field
- [ ] Run tests after migration

**When this happens:**
- Pushing migrations that drop columns without updating code
- Renaming columns without grep-ing for old names
- Multiple developers working on schema changes

---

### Error: Soft-Delete Records Block UNIQUE Constraints
**Symptom:** `duplicate key value violates unique constraint "table_column1_column2_key"`

**Root Cause:** UNIQUE constraints apply to ALL rows, but soft-delete patterns (using `left_at`, `deleted_at`, etc.) expect uniqueness only among ACTIVE records.

**Example:** User joins session, leaves (sets `left_at`), tries to rejoin:
```
# Error: Key (session_id, user_id) already exists
# Code check passes: WHERE left_at IS NULL finds no record
# Insert fails: UNIQUE constraint sees the old record
```

**Prevention:**
```sql
-- ❌ DON'T USE (blocks soft-deleted records)
UNIQUE(session_id, user_id)
UNIQUE(session_id, seat_number)

-- ✅ USE INSTEAD (partial unique index)
CREATE UNIQUE INDEX idx_session_participants_active_user
    ON session_participants(session_id, user_id)
    WHERE left_at IS NULL;

CREATE UNIQUE INDEX idx_session_participants_active_seat
    ON session_participants(session_id, seat_number)
    WHERE left_at IS NULL;
```

**Code-Level Defense (Idempotent Pattern):**
```python
def add_participant(self, session_id: str, user_id: str):
    # 1. Already active? Return existing
    existing_active = self._query(where_left_at_is_null=True)
    if existing_active:
        return existing_active

    # 2. Previously left? Reactivate
    existing_inactive = self._query(where_left_at_is_not_null=True)
    if existing_inactive:
        return self._reactivate(existing_inactive)

    # 3. Create new record
    return self._insert_new()
```

**Checklist for Soft-Delete Tables:**
- [ ] Use partial unique indexes (WHERE soft_delete_column IS NULL)
- [ ] Make insert methods idempotent (handle reactivation)
- [ ] Test: create → delete → recreate flow

**When this happens:**
- Any table using soft-delete pattern (left_at, deleted_at, is_active)
- When UNIQUE constraints don't have WHERE clause
- Rapid actions that might create duplicate insert attempts

---

### Error: Multiple Commands in Prepared Statement (PL/pgSQL Functions)
**Symptom:** `ERROR: cannot insert multiple commands into a prepared statement (SQLSTATE 42601)`

**Root Cause:** Supabase's `db push` sends each migration file through PostgreSQL's prepared statement interface. A prepared statement only supports **one command**. When a migration file contains a `CREATE FUNCTION...$$...$$;` followed by additional statements (e.g., `COMMENT ON FUNCTION`, another `CREATE FUNCTION`), PostgreSQL rejects it.

**Prevention:**
```
-- ❌ DON'T: Multiple functions + comments in one migration file
CREATE OR REPLACE FUNCTION foo() ... $$ ... $$;
COMMENT ON FUNCTION foo IS '...';
CREATE OR REPLACE FUNCTION bar() ... $$ ... $$;

-- ✅ DO: One function per migration file
-- 017_foo.sql: CREATE OR REPLACE FUNCTION foo() ... $$ ... $$;
-- 018_bar.sql: CREATE OR REPLACE FUNCTION bar() ... $$ ... $$;
```

**Additional gotcha:** Migration filenames must start with a **numeric-only** prefix. `009a_name.sql` gets **silently skipped** — use `017_name.sql` instead.

**When this happens:**
- Any migration with PL/pgSQL function definitions mixed with other statements
- Trying to use non-numeric filename prefixes (e.g., `009a_`, `009b_`)

---

*Last updated: 2026-02-11*
*Errors documented: 7*
