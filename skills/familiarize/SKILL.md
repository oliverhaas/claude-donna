---
name: familiarize
description: Use when starting work on a project or package to understand current state. Checks git state, branches, PRs, issues, plans, and merge readiness. Read-only orientation -- takes no action.
user-invocable: true
argument-hint: "[repository-path]"
---

# Familiarize

Read-only orientation skill. Gathers context from git, GitHub, and project files to produce a situation report with suggested next steps. Takes no action -- only reports.

## Process

Work through each section in order. Skip sections that don't apply (e.g., skip branch context if on main). Run all commands from the repository root.

### 1. Git State

```bash
git branch --show-current
git status --short
git stash list
```

Determine:
- Current branch name
- Dirty working tree (modified/untracked files)
- Any stashed changes

### 2. Branch Context

**If on main:** skip to section 3.

**If on a feature branch:**

```bash
# Fetch to ensure we have current remote state
git fetch origin

# Commits on this branch since diverging from main
git log --oneline origin/main..HEAD

# How far behind main
git log --oneline HEAD..origin/main

# Check for merge conflicts with main
git merge-tree $(git merge-base HEAD origin/main) HEAD origin/main | head -50
```

If `git merge-tree` shows conflict markers, note which files conflict.

Also check rebase freshness -- if the branch is more than ~20 commits behind main, flag it as a rebase candidate.

```bash
# Check for a PR on this branch
gh pr view --json number,title,state,reviewDecision,statusCheckRollup,mergeable,labels,url 2>/dev/null
```

If a PR exists, note:
- PR number, title, URL
- Review status (approved, changes requested, pending)
- CI status (passing, failing, pending)
- Merge readiness (mergeable, conflicts, blocked)

### 3. Recent Main Activity

```bash
git log --oneline origin/main -10
```

Summarize what landed recently -- helps understand the current pace and focus area.

### 4. Open PRs

```bash
gh pr list --json number,title,author,reviewDecision,statusCheckRollup,updatedAt,url --limit 10
```

For each open PR, note number, title, review status, CI status.

### 5. Open Issues

```bash
gh issue list --state open --json number,title,labels,assignees,createdAt --limit 20
```

Group by label (bugs, enhancements, etc.). Note any unassigned or unlabeled issues.

### 6. Plans and Specs

Check for active plan/spec files:

```bash
# Common plan locations
ls docs/superpowers/specs/*.md 2>/dev/null
ls PLAN.md plan.md TODO.md 2>/dev/null
ls docs/plans/*.md 2>/dev/null
```

If any plans exist, read their headers to determine if they're active or completed.

### 7. Project Orientation

Only if this is an unfamiliar project (no prior context in this conversation):

```bash
# Key project files
head -30 README.md 2>/dev/null
head -5 pyproject.toml 2>/dev/null    # name, version, description
cat CLAUDE.md 2>/dev/null
```

## Output

Present a structured situation report:

```
## Situation Report

### Current State
Branch: <branch> (<N commits ahead, M behind main>)
Working tree: clean | dirty (<list files>)
Stash: none | <N entries>
Merge conflicts with main: none | <list conflicting files>
Rebase recommended: yes (N commits behind) | no

### PR Status (if on feature branch with PR)
PR #<N>: <title> (<url>)
Reviews: <approved/changes-requested/pending>
CI: <passing/failing/pending>
Mergeable: <yes/no/conflicts>

### Recent Activity (main)
- <commit summaries, last 10>

### Open PRs
- #<N> <title> (<review status>, <CI status>)

### Open Issues
Bugs: <count> (<list titles>)
Enhancements: <count> (<list titles>)
Other: <count>
Unlabeled: <count>

### Active Plans
- <path> -- <summary>
- or: no plans found

### Suggested Next Steps
- <2-4 concrete suggestions based on all the above>
```

## Suggested Next Steps Logic

Use judgment based on what you found. Common patterns:

- **Dirty working tree** -- suggest committing, stashing, or cleaning up
- **Feature branch with passing PR and approvals** -- suggest merging
- **Feature branch with failing CI** -- suggest fixing CI failures
- **Feature branch with merge conflicts** -- suggest rebasing onto main
- **Feature branch far behind main** -- suggest rebasing
- **Feature branch with no PR** -- suggest creating a PR
- **Active plan with incomplete steps** -- suggest continuing the plan
- **Open bugs with no assignee** -- suggest picking one up
- **Open PRs needing review** -- suggest reviewing them
- **Unlabeled issues** -- suggest triaging
- **On main, clean tree, no active plan** -- suggest picking an open issue or starting new work
