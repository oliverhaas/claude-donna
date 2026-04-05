---
name: package-production-ready
description: Use when a Python package is feature-complete and needs a final review before publishing. Covers code correctness, config alignment, dependency freshness, repo hygiene, documentation accuracy, and API surface.
user-invocable: true
argument-hint: "[package-directory]"
---

# Package Production Ready

Systematic audit of a Python package before it ships. Goes beyond code correctness to cover the entire repo surface: config, deps, docs, hygiene, and API contracts.

## When to Use

- Package is feature-complete and you want to verify it's ready to publish
- Before cutting a release or tagging a version
- After a batch of features landed and you need a final sweep

## Process

Two phases: **audit** then **fix**.

1. Work through each checklist section, collecting findings into a structured report. Do not change anything yet.
2. Present all findings as a plan grouped by section. Wait for user approval before making any changes.
3. After approval, fix the approved items. Run the full quality gate once at the end (tests + linter + type checker).

## Setup

Determine the package directory from `$ARGUMENTS` or the current working directory. Identify:

- **Package name** -- the pip-installable name (from `pyproject.toml` `[project] name`)
- **Module name** -- the importable name (from `[tool.hatch.build.targets.wheel] packages` or derived from package name)
- **Type checker** -- `mypy` or `ty` (from pyproject.toml config and pre-commit config)

---

## Audit Checklist

### 1. Type Checking and Linting

Run all configured checkers and collect output:

```bash
uv run ruff check <module>/
uv run ruff format --check <module>/
# whichever type checker is configured:
uv run mypy <module>/
# or
uv run ty check <module>/
```

Also check for:

- Stale `type: ignore` or `type: ignore[code]` comments where the underlying issue was resolved
- `type: ignore` comments using the wrong error code
- Differences between local and CI type checker environments (e.g. different Python versions, different strict flags)

### 2. Tests

```bash
uv run pytest
```

- Every test that touches the DB has `@pytest.mark.django_db` (or equivalent)
- Test names accurately describe what they test
- Tests that create resources clean them up (context managers, finally blocks)
- Config options and feature flags have at least one test exercising them
- No tests that pass by accident (relying on implicit fixture side effects, testing nothing)

### 3. Code Review

Review ALL source files in the package -- not just a diff, the entire codebase. Use the review skill as a reference for what to check, but adapt it for full-package review rather than diff review.

Read every source file and check for:

- Bugs, logic errors, off-by-one errors
- Unhandled edge cases, missing None checks
- Resource leaks (unclosed connections, files, cursors)
- Exception safety (bare except, swallowed exceptions, except blocks that hide the cause)
- API contract violations (function returns different types than annotated, missing required kwargs)
- Dead code (unused functions, unreachable branches, commented-out code)
- Circular imports or import-time side effects

For large packages, use parallel review agents to cover different modules concurrently.

### 4. Dependency Freshness

```bash
# Check each dependency for latest version
pip index versions <dependency-name>
```

- Flag outdated dev dependencies (ruff, mypy, pytest, etc.)
- Flag outdated runtime dependencies
- Note: after updating, type checker and tests must be re-run (new stubs can change what's valid)
- Check that `uv.lock` is committed and up to date (`uv lock --check`)

### 5. Config Alignment

Check that these all agree where applicable:

| Setting | Where |
|---|---|
| Minimum Python version | `requires-python` in pyproject.toml |
| mypy `python_version` | pyproject.toml `[tool.mypy]` |
| ruff `target-version` | pyproject.toml `[tool.ruff]` |
| ty `python-version` | pyproject.toml `[tool.ty.environment]` |
| Classifiers | `Programming Language :: Python :: 3.X` |
| CI matrix | `.github/workflows/` |
| `.python-version` | root file |
| pre-commit `default_language_version` | `.pre-commit-config.yaml` |

**Rule: type checkers and ruff should target the minimum supported version** so they catch features unavailable on older Pythons. `.python-version` and pre-commit language version should use the latest supported version.

### 6. Documentation Accuracy

- README feature list matches what's actually implemented (no aspirational features, no removed features still listed)
- All user-facing settings/config options are documented (search source for `getattr(settings,`, `app_settings`, or equivalent patterns)
- Architecture/approach description matches current code (not stale from early development)
- Quick-start example actually works if copy-pasted
- Changelog is up to date with recent changes
- No style violations per project preferences

### 7. Repo Hygiene

- No stale planning docs (PLAN.md, TODO.md, NOTES.md) that shouldn't ship
- No leftover worktree directories or merge artifacts
- `.gitignore` covers build artifacts, editor files, venv
- No secrets, credentials, or `.env` files committed
- No unnecessary files that would be included in the sdist/wheel

### 8. API Surface

- `__init__.py` exports match the public API (no missing or stale exports)
- `__all__` is defined and accurate if the package uses it
- Exported names work when imported (no circular import issues at import time)
- Entry points (pytest plugins, Django app configs) are correctly registered in pyproject.toml
- Django AppConfig doesn't set unnecessary attributes (e.g. `default_auto_field` when there are no models)

### 9. Packaging

- Version string is appropriate for the release (not `0.0.1-dev` if you're shipping)
- `[build-system]` is configured
- Package includes only what it should (check `[tool.hatch.build]` includes/excludes)
- LICENSE file exists and matches pyproject.toml `license` field
- `py.typed` marker exists if `Typing :: Typed` classifier is declared
- Development status classifier matches the actual status (Pre-Alpha, Alpha, Beta, Production/Stable)

### 10. Git History

Review the commit log for issues. **Do not rewrite history -- only report findings.**

```bash
git log --oneline --all -50
git log --format="%H %an <%ae> %s" -50
```

Flag any of:

- Unwanted attribution (Co-authored-by trailers, "Generated by" comments)
- WIP/fixup commits that should be squashed
- Redundant back-and-forth commits (add X, remove X, add X back)
- Commits that fix the previous commit (candidates for squashing)
- Inconsistent commit message style

Report findings with specific commit SHAs. Recommend whether a rebase is worthwhile based on:

- **Pre-release (0.x, alpha, beta):** recommend rewriting freely
- **Released (1.0+):** recommend rewriting only from latest release tag forward

---

## Presenting Findings

After completing all sections, present a structured report:

```
## Audit Results

### Blockers (must fix before release)
- [section] description of issue

### Improvements (should fix)
- [section] description of issue

### Suggestions (nice to have)
- [section] description of issue

### Git History
- [commit SHA] description of issue
- Recommendation: [rebase/leave as-is]

### Clean
- [list sections with no issues found]
```

Wait for user approval before making any changes. The user may choose to fix all, fix only blockers, or adjust the list.

## After Approval

1. Fix approved items
2. Run the full quality gate:
   ```bash
   uv run ruff check <module>/
   uv run ruff format --check <module>/
   uv run mypy <module>/  # or ty
   uv run pytest
   ```
3. If the quality gate passes, report success
4. If it fails, fix and re-run until clean
