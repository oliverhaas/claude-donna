---
name: review
description: Review the current branch changes using focused, sequential passes. Each pass checks only one specific area based on project instruction files.
disable-model-invocation: true
---

# Task: Review

Review the current branch changes using focused, sequential passes. Each pass checks only one specific area based on project instruction files.

## Phase 1: Automated Quality Gates

### Step 1: Check for PR and CI Status

```bash
git branch --show-current
gh pr view 2>/dev/null
```

**If PR exists:**
- Check CI status from the PR output
- If CI checks failed or have errors, report failures and **stop**
- If CI checks passed, proceed to Phase 2

**If no PR exists:**
Run checks locally with reduced parallelism:
```bash
uv run pytest -n 3
uv run ruff check
uv run ruff format --check
uv run mypy .
```

If any check fails, report failures and **stop**.

## Phase 2: Focused Review Passes

Get the diff against remote main (fetch first to ensure it's current):
```bash
git fetch origin
git diff origin/main...HEAD
```

For each pass:
1. **Read** the referenced instruction file(s)
2. **Examine** ONLY the changed code in the diff
3. **Check** ONLY for issues described in the instruction file(s)
4. **Note** findings before moving to the next pass
5. **Skip** the pass if no relevant code was changed

### Pass 1: Python Fundamentals
@.claude/skills/general-python/SKILL.md

### Pass 2: Django ORM
@.claude/skills/django-orm-queries/SKILL.md
@.claude/skills/django-modern-patterns/SKILL.md

### Pass 3: Models
@.claude/skills/django-data-migrations/SKILL.md
@.claude/skills/django-save-hooks/SKILL.md

### Pass 4: Services & Fat Models
@.claude/skills/django-services/SKILL.md
@.claude/skills/django-fat-models/SKILL.md

### Pass 5: Views & Templates
@.claude/skills/django-views/SKILL.md
@.claude/skills/django-formwork-icons/SKILL.md

### Pass 6: Validation & Data Containers
@.claude/skills/django-validation/SKILL.md
@.claude/skills/python-data-containers/SKILL.md

### Pass 7: Celery Tasks
@.claude/skills/celery-tasks/SKILL.md

### Pass 8: Testing
@.claude/skills/tests-general/SKILL.md
@.claude/skills/django-factories/SKILL.md
@.claude/skills/tests-celery/SKILL.md
@.claude/skills/tests-view/SKILL.md
@.claude/skills/tests-playwright-e2e/SKILL.md

### Pass 9: Logging
@.claude/skills/logging/SKILL.md

### Pass 10: API Clients
@.claude/skills/api-clients/SKILL.md

### Pass 11: Alpine.js
@.claude/skills/alpine-js/SKILL.md
@.claude/skills/alpine-htmx/SKILL.md

## Phase 3: Cross-Cutting Checks

### Unused Code Detection
When code is removed or refactored in the diff, check if it leaves behind unused code:
- If a function call is removed, check if that function is still used elsewhere
- If an import is removed, check if the imported module/function is still needed
- Look for orphaned helper functions, constants, or classes

### Categorizing Findings
- **Request changes**: Issues that must be fixed (bugs, N+1 queries, security, failing tests)
- **Suggestions**: Non-blocking improvements that can be addressed in follow-up work

Present suggestions separately at the end of the review as "potential follow-ups".

## Notes

- Focus on the diff, not unchanged code
- Each pass checks ONLY its specific area
- Skip irrelevant passes
- Don't check style -- ruff handles that
- Include file paths and line numbers in findings
