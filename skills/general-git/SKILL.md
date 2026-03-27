---
name: general-git
description: Git workflow practices for GitHub-based development. Use when creating branches, committing, pushing, or creating pull requests.
user-invocable: false
---

# Git Workflow Guidelines

Follow these git practices for consistent development workflow. We're using GitHub.

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

## Squash Commits

**Default squashing behavior:**
- GitHub repository is configured to squash commits by default when merging
- No additional CLI flags needed - the repository setting handles this automatically
- Feature branch commits will be squashed into a single commit on merge


---
