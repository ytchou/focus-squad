---
allowed-tools: Bash(git:*), Bash(gh:*), Bash(npm:*), Bash(cd:*), Bash(sleep:*), Bash(source:*), Bash(./venv/*), Read, Grep, Glob, Edit
argument-hint: [type: feature|fix|refactor|docs|config] (optional)
description: Create a PR with Focus Squad context and smart descriptions
---

# Create Pull Request for Focus Squad

## Current State
- Branch: !`git branch --show-current`
- Changed files: !`git diff --name-only main...HEAD`
- Commits: !`git log --oneline main...HEAD`

## Project Context
@PRD.md
@SPEC.md
@CLAUDE.md

## Instructions

Create a pull request following these steps:

### Phase 1: Pre-flight Checks

1. **Run Formatters** (BEFORE committing):
   - Backend: `cd backend && ./venv/bin/ruff format . && ./venv/bin/ruff check --fix .`
   - Frontend: `cd frontend && npm run format`

2. **Stage and Commit** any formatting changes

### Phase 2: Analyze & Create PR

3. **Analyze Changes**: Review the git diff to understand what changed

4. **Classify Type**: $1 if provided, otherwise auto-detect from changes
   - feature: New functionality
   - fix: Bug correction
   - refactor: Code improvement
   - docs: Documentation only
   - config: Configuration/DevOps changes

5. **Identify Layers**: Detect affected areas
   - frontend/ → Next.js/React changes
   - backend/ → FastAPI/Python changes
   - supabase/migrations/ → Database changes

6. **Generate PR** using this template:

## Summary
[1-3 bullets: WHAT changed and WHY]

## Type
- [ ] feature: New functionality
- [ ] fix: Bug correction
- [ ] refactor: Code improvement
- [ ] docs: Documentation only
- [ ] config: Configuration/DevOps changes

## Affected Layers
- [ ] Frontend (Next.js/React)
- [ ] Backend (FastAPI/Python)
- [ ] Database (Supabase/PostgreSQL)
- [ ] Config/DevOps

## Changes
[Key changes list with file paths]

## Checklist
- [ ] No secrets or .env files
- [ ] Type hints on all Python functions
- [ ] Pydantic models for API I/O
- [ ] Tailwind only (no CSS files)

---
Generated with Claude Code /create-pr command

7. **Execute**:
   a. Check if a PR already exists for the current branch: `gh pr view --json number,body`
   b. If **no PR exists**: Run `gh pr create --title "[type]: description" --body "..."` using the exact type from the checked Type box above
   c. If **PR already exists**:
      - Push any new commits to the branch
      - Analyze what the new commits change
      - Read the existing PR body, add new bullet(s) to the `## Summary` section describing the latest changes
      - Update the PR body using `gh pr edit --body` with the appended summary
      - Do NOT overwrite or remove existing summary bullets or title

### Phase 3: CI/CD Verification (MANDATORY)

8. **Wait for CI**: After push, wait ~60-70 seconds then check CI status:
   ```bash
   gh run list --branch <branch-name> --limit 4
   ```

9. **If CI Fails**: Auto-fix and retry (up to 3 attempts):

   a. **Check failure logs**:
      ```bash
      gh run view <run-id> --log-failed | head -100
      ```

   b. **Common fixes**:
      - **Ruff lint/format errors**: Run `ruff check --fix` and `ruff format`
      - **Prettier errors**: Run `npm run format`
      - **ESLint errors**: Fix the specific issues (any types, unescaped entities, hook deps)
      - **TypeScript errors**: Fix type issues in the code
      - **Import sorting**: Ruff handles this with `--fix`

   c. **Commit fixes** with message: `fix(ci): [description of fix]`

   d. **Push and wait** for CI again

   e. **Repeat** until all checks pass

10. **Confirm Success**: Only report PR as ready when ALL checks show `completed success`:
    ```bash
    gh pr checks <pr-number>
    ```

### Completion Criteria

The PR is NOT complete until:
- [ ] All CI checks pass (Backend CI, Frontend CI, SQL Lint, Security)
- [ ] PR URL is provided to user
- [ ] Summary of any CI fixes made is provided
