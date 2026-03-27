---
name: github-issues
description: Working with GitHub issues for tracking bugs, tasks, and features. Reference when creating issues, linking commits/PRs, or triaging.
user-invocable: false
---

# GitHub Issues

## Creating Issues

Use the `gh` CLI:

```bash
gh issue create --title "Bug: widget fails on empty input" --body "Steps to reproduce..."
gh issue create --title "Add export feature" --label enhancement
```

## Referencing Issues

Link issues in commit messages and PR descriptions:

- `fixes #123` or `closes #123` -- auto-closes the issue when the PR merges
- `refs #123` -- references without closing

Use these in commit message bodies, not titles.

## Labels

Standard labels:

- `bug` -- something is broken
- `enhancement` -- new feature or improvement
- `chore` -- maintenance, refactoring, dependencies
- `documentation` -- docs-only changes

## CLI Quick Reference

```bash
gh issue list                          # open issues
gh issue list --state closed           # closed issues
gh issue list --label bug              # filter by label
gh issue view 123                      # view issue details
gh issue close 123                     # close an issue
gh issue comment 123 --body "Fixed in abc1234"
```

---
