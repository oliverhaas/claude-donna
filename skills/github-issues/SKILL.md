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

- `fixes #123` or `closes #123` auto-closes the issue when the PR merges
- `refs #123` references without closing

Use these in commit message bodies, not titles.

## Labels

Standard labels:

- `bug`: something is broken
- `enhancement`: new feature or improvement
- `chore`: maintenance, refactoring, dependencies
- `documentation`: docs-only changes

## CLI Quick Reference

```bash
gh issue list                          # open issues
gh issue list --state closed           # closed issues
gh issue list --label bug              # filter by label
gh issue view 123                      # view issue details
gh issue close 123                     # close an issue
gh issue comment 123 --body "Fixed in abc1234"
```

## Lifecycle Rules

### File requested issues immediately

When the user says "file an issue for X", do it now. Don't defer to "after the PR merges" or bundle it with other work. Filing is one `gh issue create` call; deferral is how issues get forgotten.

### Never close issues autonomously

Closing an issue is the user's call, never yours. Don't close after merging a PR unless the user explicitly said so or the PR body has `Closes #N` and the merge fires GitHub's auto-close. If unsure, leave it open and ask.

### Link PRs to issues on merge

When a PR merges that resolves an issue, comment on the issue with the PR number and merge commit:

```bash
gh issue comment 123 --body "Resolved in #456 (commit abc1234)"
```

Then close the issue (if appropriate per the rule above). This makes the issue's history traceable to the change that fixed it.

### Edit the body, don't pile up status comments

When updating an issue with new context (scope changes, additional findings, design notes), edit the issue body or maintain one pinned tracking comment:

```bash
gh issue edit 123 --body "$(cat <<'EOF'
## Updated description with new findings
...
EOF
)"
```

Threading new status comments on every update buries the actual issue under noise. Use a single comment that you edit, or update the body itself.

### Fork-aware issue commands

In a fork, every `gh issue ...` defaults to upstream. Pass `--repo me/foo` explicitly to target the fork:

```bash
gh issue create --repo me/foo --title "..." --body "..."
```

See `general-git` → "Fork-Aware Defaults".

---
