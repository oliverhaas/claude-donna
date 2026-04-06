# claude-donna

Personal Claude Code plugin: skills, agents, and hooks for the full stack.

## Install

```bash
/plugin marketplace add oliverhaas/claude-donna
/plugin install donna
```

## Skills

### `/bark`: Rapid-fire voice dispatch

Dictate changes in a stream of consciousness. Each discrete change gets parsed, dispatched to a background agent in its own git worktree, and auto-merged back.

```
/bark
"the help icon should be blue not gray"
"detail page is throwing a template error, probably from the django-tables2 upgrade"
"pagination is off-center on the list view"
/bark status
```

### `/review`: Multi-pass code review

Sequential review passes across Python, Django, ORM, services, testing, and more.

### `/pr`: Pull request workflow

Branch, commit, push, and open a draft PR with CI checks.

### `/triage`: GitHub issue triage

Scan unlabeled issues, apply labels, flag duplicates.

### `/merge-rebase`: Rebase current branch

Fetch, merge origin/main, handle conflicts, push.

### `/lessons`: Session retrospective

Extract patterns from the conversation and propose codified rules.

### Non-invocable skills

Reference skills loaded automatically when relevant: Django (ORM, validation, factories, services, fat models, views, migrations, save hooks, modern patterns, formwork icons), Alpine.js (core patterns, HTMX integration), Celery, Playwright E2E, Python conventions, git workflow, logging, security, and more.

## Companion plugins

- **[superpowers](https://github.com/anthropics/claude-code-superpowers)**: Project planning, brainstorming, and feature design. Pairs well with donna's execution-focused skills.

## License

MIT
