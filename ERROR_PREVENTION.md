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

*Last updated: 2026-02-01*
*Errors documented: 2*
