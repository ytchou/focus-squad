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

*Last updated: 2026-02-02*
*Errors documented: 4*
