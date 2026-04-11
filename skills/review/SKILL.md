---
name: review
description: Review the current branch changes using focused, sequential passes. Each pass checks only one specific area based on plugin skill files.
user-invocable: true
---

# Task: Review

Review the current branch changes using focused, sequential passes. Each pass checks only one specific area based on plugin skill files.

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
${CLAUDE_PLUGIN_ROOT}/skills/general-python/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/type-annotations/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/error-handling/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/general-security/SKILL.md

### Pass 2: Django ORM & Database
${CLAUDE_PLUGIN_ROOT}/skills/django-orm-queries/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-modern-patterns/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/postgresql/SKILL.md

### Pass 3: Models & Migrations
${CLAUDE_PLUGIN_ROOT}/skills/django-data-migrations/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-save-hooks/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-signals/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/zero-downtime-migrations/SKILL.md

### Pass 4: Services & Fat Models
${CLAUDE_PLUGIN_ROOT}/skills/django-services/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-fat-models/SKILL.md

### Pass 5: Views, Templates & Middleware
${CLAUDE_PLUGIN_ROOT}/skills/django-views/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-templates/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-jinja2/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-jinjafy/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-middleware/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-formwork-icons/SKILL.md

### Pass 6: Validation, Settings & Permissions
${CLAUDE_PLUGIN_ROOT}/skills/django-validation/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/python-data-containers/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-settings/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-permissions/SKILL.md

### Pass 7: Admin
${CLAUDE_PLUGIN_ROOT}/skills/django-admin/SKILL.md

### Pass 8: Caching & Performance
${CLAUDE_PLUGIN_ROOT}/skills/django-caching/SKILL.md

### Pass 9: Celery Tasks & Async
${CLAUDE_PLUGIN_ROOT}/skills/celery-tasks/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-asyncio/SKILL.md

### Pass 10: Testing
${CLAUDE_PLUGIN_ROOT}/skills/tests-general/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-factories/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/tests-celery/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/tests-view/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/tests-playwright-e2e/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/django-tdd/SKILL.md

### Pass 11: Logging & API Clients
${CLAUDE_PLUGIN_ROOT}/skills/logging/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/api-clients/SKILL.md

### Pass 12: Frontend
${CLAUDE_PLUGIN_ROOT}/skills/alpine-js/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/alpine-htmx/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/htmx/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/tailwind-css/SKILL.md
${CLAUDE_PLUGIN_ROOT}/skills/daisyui/SKILL.md

## Phase 3: Cross-Cutting Checks

### Unused Code Detection
When code is removed or refactored in the diff, check if it leaves behind unused code:
- If a function call is removed, check if that function is still used elsewhere
- If an import is removed, check if the imported module/function is still needed
- Look for orphaned helper functions, constants, or classes

### Categorizing Findings
- **Request changes**: issues that must be fixed (bugs, N+1 queries, security, failing tests)
- **Suggestions**: non-blocking improvements that can be addressed in follow-up work

Present suggestions separately at the end of the review as "potential follow-ups".

## Notes

- Focus on the diff, not unchanged code
- Each pass checks ONLY its specific area
- Skip irrelevant passes
- Don't check style; ruff handles that
- Include file paths and line numbers in findings
