---
name: triage
description: Scan open GitHub issues with no labels, analyze them, and apply appropriate labels.
user-invocable: true
---

# GitHub Issues Triage

Scan open issues that have no labels, analyze each one, and apply appropriate labels.

## Step 1: Find Unlabeled Issues

```bash
gh issue list --state open --label "" --json number,title,body,createdAt,comments --limit 50
```

If no unlabeled issues are found, report that and stop.

## Step 2: Analyze and Label Each Issue

For each unlabeled issue, read the title and body. Apply one or more labels from this set:

**Type labels (pick one):**
- `bug`: something is broken or producing incorrect results
- `enhancement`: new feature or improvement to existing functionality
- `documentation`: docs missing, incorrect, or need improvement
- `question`: user asking for help, not reporting a bug

**Effort labels (pick one if clear):**
- `good-first-issue`: small scope, well-defined, good for new contributors

**Priority labels (pick one):**
- `priority:high`: data loss, security issue, blocking workflow, or widespread breakage
- `priority:low`: cosmetic, minor inconvenience, or nice-to-have

Apply labels:
```bash
gh issue edit {NUMBER} --add-label "bug,priority:high"
```

## Step 3: Detect Duplicates

If two or more open issues describe the same problem:
- Keep the oldest issue (or the one with more discussion)
- Comment on the duplicate linking to the original
- Close the duplicate

```bash
gh issue comment {DUPLICATE_NUMBER} --body "Duplicate of #{ORIGINAL_NUMBER}. Closing."
gh issue close {DUPLICATE_NUMBER}
```

## Step 4: Flag Stale Issues

Issues older than 90 days with no comments or activity: add a `stale` label.

```bash
gh issue edit {NUMBER} --add-label "stale"
```

## Step 5: Output Summary

```
## Triage Summary

### Labeled
- #12 "Login fails on mobile" (bug, priority:high)
- #15 "Add dark mode" (enhancement, priority:low)

### Closed as Duplicate
- #18 "Login broken on phone" (duplicate of #12)

### Marked Stale
- #3 "Old feature idea" (no activity since 2024-01-15)

Total: X triaged, Y labeled, Z duplicates closed, W marked stale
```
