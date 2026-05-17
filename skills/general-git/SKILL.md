---
name: general-git
description: Git workflow practices for GitHub-based development. Use when creating branches, committing, pushing, or creating pull requests.
user-invocable: false
---

# Git Workflow Guidelines

Follow these git practices for consistent development workflow. We're using GitHub.

## Never Commit Directly to Main

Feature work, fixes, and refactors go on a branch — never directly on `main`. The single exception is when the user explicitly asks for a direct commit on a personal repo (and even then, confirm if the change is non-trivial).

Before any commit:

```bash
git branch --show-current  # confirm not main
```

If you're on main and the task is anything beyond a trivial doc/typo fix, create a branch first:

```bash
git checkout -b <type>/<short-description>
```

Use a worktree (`superpowers:using-git-worktrees` or `git worktree add`) for feature work that takes more than a single session — keeps unrelated WIP from contaminating the branch.

## Keep Branches Single-Purpose

One branch, one concern. Don't mix:

- A feature change with an unrelated refactor sweep.
- A bug fix with a translation/locale update.
- Two unrelated fixes "while you're in there".

When staging, add specific files (`git add path/to/file`) rather than `git add .` — the wildcard sweeps in unrelated edits (translation files, lockfiles, scratch notes) that don't belong in the branch.

## Branch and Pull Request Creation

**Branch naming format:** `<type>/<issue-number>-<short-description>` (or `<type>/<short-description>` without issue)

The branch prefix should match the commit type (see commit-guidelines rule).

**Examples:**
```bash
git checkout -b feat/123-implement-feature
git checkout -b fix/456-bug-regarding-something
git checkout -b chore/789-update-dependencies
git checkout -b refactor/101-optimize-query
git checkout -b docs/improve-rules
```

**Push and create pull request:**
```bash
# Push branch first
git push --set-upstream origin <branch>

# Create PR with custom title and description
gh pr create --title "feat(#123): implement new feature" --body "Closes #123"
```

## Pull Request Requirements

**PR titles MUST follow commit message conventions for CI:**
- `feat(#123): implement new feature`
- `fix(#456): resolve authentication bug`
- `refactor(#789): simplify payment logic`

**PR descriptions automatically reference the associated issue from title:**
- Example: `Closes #123`

## Staying Current

**Regularly rebase against main to prevent drift:**
```bash
git fetch origin
git rebase origin/main
```

**Use force-with-lease after rebase:**
```bash
git push --force-with-lease
```

## Pre-Push Hygiene

Run the local checks that CI will run anyway, before pushing:

```bash
uv run ruff format
uv run ruff check
uv run mypy .   # or `uv run ty check .` on non-Django projects
git status      # confirm clean
git branch --show-current  # confirm correct branch
```

A failed CI run on a lint issue you could have caught locally is wasted CI time and a wasted notification for reviewers. Don't suppress lint/type errors to make CI green — fix the root cause.

If CI fails after a rebase, check the same job's status on `main` first — a flaky job on main isn't your branch's problem.

## Squash Commits

**Default squashing behavior:**
- GitHub repository is configured to squash commits by default when merging
- No additional CLI flags needed - the repository setting handles this automatically
- Feature branch commits will be squashed into a single commit on merge


---
