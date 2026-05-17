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

## Fork-Aware Defaults

If the working repo is a fork, every git/GitHub operation defaults to the fork (`origin`), not the upstream remote. Get this wrong and you push a feature branch to someone else's repo, or open a PR against upstream when you meant to open it against your own fork.

Before pushing or creating a PR, check remotes:

```bash
git remote -v
# origin     git@github.com:me/foo.git    (push)
# upstream   git@github.com:owner/foo.git (push)
```

If both `origin` and `upstream` are configured, this is a fork. Then:

```bash
# Push to fork's branch (default)
git push --set-upstream origin <branch>

# Create PR against the fork's default branch. Pass --repo explicitly.
gh pr create --repo me/foo --base main --title "..." --body "..."
```

Never call `gh pr create` without `--repo` in a fork. The default target is the upstream remote, which is almost always wrong.

Same rule for issues:

```bash
gh issue create --repo me/foo --title "..." --body "..."
```

The `check_pr_target.py` hook prints the resolved target before any `gh pr create` runs. If it flags a fork mismatch, fix `--repo` before retrying.

## Worktree Discipline

When the user signals they're mid-work on something else before requesting new feature work, propose a worktree before starting. Use `superpowers:using-git-worktrees` or `git worktree add`.

Within a session:

- **Remember the base branch.** Once the user specifies a worktree base ("branch off `develop`"), that's the default for every subsequent worktree this session. Don't re-ask.
- **"Drop the worktree" / "do it directly here" = leave immediately.** Switch back to the main working tree, no confirmation needed.
- **Confirm worktree state in the completion summary.** When work is done in a worktree, the wrap-up message should include current worktree path, branch, and whether the worktree should be removed.

## Code-Generated Files

Before editing files in an unfamiliar repo, check whether any are code-generated (look for `# DO NOT EDIT`, `// @generated`, `*.pb.go`, OpenAPI schemas, Cython `.c` files next to `.pyx`, Rust `bindings.rs`). If so, edit the source and re-run the project's generation workflow. Don't hand-edit the output.

---
