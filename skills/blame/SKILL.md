---
name: blame
description: "Investigate the history behind code or behavior. Traces changes through git blame, commits, PRs, issues, and external systems."
user-invocable: true
argument-hint: "<what to investigate>"
---

# Blame

Supercharged git blame. Investigate the full history behind code, a behavior, or a bug, chasing references across git, GitHub, ticket systems, logs, and any other available resource until the trail goes cold.

## Input

`$ARGUMENTS` is free-text. It could be:

- A file path or line range: `src/patch.py:450-460`
- A function or symbol name: `handle_eager`
- A question: `why is prefetch_one_level wrapped twice`
- A problem description: `the false positive on converging FK chains`
- Any combination

Interpret the input and figure out where to start.

## Investigation

There is no fixed sequence. Use judgment and chase every reference you find. Available tools, roughly ordered by how often you'll reach for them:

**Git**
- `git blame` on the relevant lines
- `git log -p` / `git show` for commit details and diffs
- `git log --follow` to trace through renames
- `git log -S`/`-G` to search for when a string or pattern was added/removed
- `git bisect` if narrowing down a regression

**GitHub**
- `gh pr list --search <sha>` or `gh pr list --search <keyword>` to find related PRs
- `gh pr view <number>` for PR description, review comments, linked issues
- `gh issue view <number>` for issue context

**External systems**
- If commits, PRs, or issues reference external tickets (Jira, Linear, etc.) and an MCP is available, follow those references
- If the user provided logs or an observability MCP is available, check there for runtime context
- If a CLAUDE.md or similar doc references design decisions, read it

**Keep going.** If a commit message says "see #42", read issue #42. If the issue says "per discussion in JIRA-123", check JIRA-123 if you can. If a PR links to a spec doc, read the spec. Stop when the answer is clear or the trail is cold.

## Output

Present a structured investigation report:

```
## Investigation: <short title>

### What
<What code or behavior was investigated: file, function, lines>

### Who
<Author(s) involved, with commit attribution>

### When
<Timeline of relevant changes, from oldest to newest>

### Why
<The motivation, pieced together from commit messages, PRs, issues,
tickets, logs, design docs, or any other source>

### How
<The actual changes that produced the current state: what was added,
removed, refactored, and in what order>

### References
- <commit SHAs, PR links, issue links, ticket links: everything consulted>
```

Omit sections that don't apply (e.g., skip "Who" if it was a single author and the answer is obvious). Keep each section concise. The value is in connecting the dots, not in repeating raw git output.

---
