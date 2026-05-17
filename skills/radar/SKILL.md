---
name: radar
description: "Daily orientation dashboard. Surfaces open issues across the repos you've been working on lately, plus your open PRs and review requests. Run when you don't know where to start."
user-invocable: true
argument-hint: "[issues | prs]"
---

# Radar

Cross-repo situational overview, focused on the repos you've actually been touching. Use when you want a quick scan of what's waiting for you.

## Arguments

`/radar [section]` where section is optional:

| Invocation | Sections |
|------------|----------|
| `/radar` | issues + prs |
| `/radar issues` | issues only |
| `/radar prs` | prs only |

If an invalid section name is given, print: "Unknown section. Valid options: `issues`, `prs`" and stop.

## Step 0: Detect Current User

```bash
ME=$(gh api user --jq '.login')
```

If this fails (gh not authenticated), report it and stop.

## Step 1: Determine Recent Repos

"Recent" = repos with commits authored by me in the last ~3 months. Commits (not PRs) because the user often pushes directly to main on personal repos.

```bash
gh search commits --author=@me --sort=committer-date --order=desc --limit=100 \
  --json repository,commit \
  --jq '[.[] | {repo: .repository.nameWithOwner, date: .commit.committer.date}]
        | group_by(.repo)
        | map({repo: .[0].repo, last: (max_by(.date).date)})
        | sort_by(.last) | reverse | .[0:10] | .[].repo'
```

Save as `RECENT_REPOS` (one repo per line, max 10). If empty, fall back to `gh repo list --limit 10 --sort pushed --json nameWithOwner --jq '.[].nameWithOwner'`.

---

## Section: Issues

### 1a. Open Issues in Recent Repos

For each repo in `RECENT_REPOS`, fetch open issues (cap at 15 per repo, newest first):

```bash
gh issue list --repo {repo} --state=open --limit=15 \
  --json number,title,author,labels,createdAt,assignees,updatedAt \
  --jq 'sort_by(.createdAt) | reverse'
```

Skip repos that return zero issues.

### 1b. Assigned to You

Across all repos:

```bash
gh search issues --assignee=@me --state=open --limit=20 \
  --json number,title,repository,labels,updatedAt
```

### 1c. Authored by You

Open issues you opened (often "things I noticed but haven't fixed yet"):

```bash
gh search issues --author=@me --state=open --limit=20 \
  --json number,title,repository,labels,createdAt
```

### Issues Output

```
### Recent activity per repo
oliverhaas/django-filthyfields
  #42  Type hints break with custom managers           [bug]            2d ago
  #41  Document the check_relationship parameter       [docs]           5d ago

oliverhaas/celery-redis-plus
  #18  Connection pool leak under load                 [bug, priority]  1d ago

### Assigned to you
  oliverhaas/django-cachex#7  Cache invalidation race  [bug]   updated 3h ago

### Authored by you (still open)
  oliverhaas/some-other-repo#12  Investigate flaky test on Python 3.13   opened 2w ago
```

Per row: number, title (truncate at ~55 chars), labels in brackets, age. If a subsection is empty, print "None" under the heading.

---

## Section: PRs

### 2a. Your Open PRs

Across all repos:

```bash
gh search prs --author=@me --state=open --limit=50 \
  --json number,title,repository,url,isDraft,reviewDecision,statusCheckRollup,updatedAt
```

For each PR, derive:
- CI status from `statusCheckRollup`: roll up to `PASS` / `FAIL` / `PENDING` / `NONE`
- Draft flag from `isDraft`
- Review decision: `APPROVED` / `CHANGES_REQUESTED` / `REVIEW_REQUIRED` / `null`

### 2b. PRs Awaiting Your Review

```bash
gh search prs --review-requested=@me --state=open --limit=50 \
  --json number,title,author,repository,url,statusCheckRollup,updatedAt
```

### PRs Output

```
### Your open PRs
  oliverhaas/django-filthyfields !23   feat: add prefetch helper          [PASS]  [APPROVED]   2d
  oliverhaas/celery-redis-plus   !12   fix: race in pool release          [FAIL]  [REVIEW_REQUIRED]   4h
  oliverhaas/django-cachex       !8    Draft: rewrite invalidation        [PEND]  [DRAFT]      1d

### Awaiting your review
  oliverhaas/some-repo !55   refactor: extract handler  by alice     [PASS]   opened 3d ago
```

Per row: repo + PR number, title (truncate at ~50 chars), CI marker, review/draft marker, age. Sort each subsection: failing CI first, then by age (oldest at top).

If both subsections are empty, print: "No open PRs and no review requests."

---

## After the Summary

Offer concrete next actions:

> Want me to dig into anything? For example:
> - "Look at #N in <repo>" — fetch full issue/PR details
> - "Pick up #N" — assign issue to you and check it out as a branch
> - "Review PR !N" — pull down and review the PR
> - "Rebase PR !N" — merge main into the PR branch
> - "Fix CI on !N" — investigate failing checks

### Action Delegation

| User says | Delegate to |
|-----------|-------------|
| "Look at #N" | `gh issue view N --repo <repo>` (or `gh pr view`) and summarise |
| "Pick up #N" | `gh issue edit N --repo <repo> --add-assignee @me` then create a branch |
| "Review PR !N" | Check out the branch, then run the `review` skill |
| "Rebase PR !N" | Check out the branch, run the `merge-rebase` skill |
| "Fix CI on !N" | Fetch failing logs via `gh run view --log-failed`, diagnose, fix |

## Notes

- All `gh search` commands respect GitHub's search rate limits (30/min unauth, generous when auth'd). If a query 403s on rate limit, back off and retry once.
- "Recent repos" is intentionally bounded at 10 to keep output skimmable. Increase the cap in Step 1 if you regularly bounce across more repos.
- Skip a section if its prerequisites fail; never skip the whole skill.
