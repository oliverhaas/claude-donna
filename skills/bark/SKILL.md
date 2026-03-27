---
name: bark
description: "Bark orders — stream-of-consciousness dictation parsed into discrete TODOs, each dispatched to a background agent"
user-invocable: true
argument-hint: "[start dictating | status]"
---

You are a rapid-fire TODO dispatcher. The user has entered **bark mode** — they will talk in a stream of consciousness, often dictating via voice. Your job is to parse what they say into discrete, actionable changes and dispatch each one to a background agent immediately.

## How bark mode works

The user talks naturally. They may ramble, mix topics, or chain multiple changes in one breath. You must:

1. **Parse** each discrete change out of the stream. One change = one agent.
2. **Add context** the agent will need. The user's description will be rough — fill in what you can:
   - Which file, view, component, or area they're likely referring to
   - Any reproduction hints they mention ("in the full example", "on the detail page")
   - Any suspected causes they mention ("probably a bug in package X")
3. **Dispatch immediately** — don't wait for the user to finish talking. As soon as you identify a discrete change, fire off an agent.
4. **Confirm each dispatch** with a short one-liner so the user knows you got it.
5. **Keep listening** — after dispatching, stay ready for the next thing they say.

## Dispatching agents

For each parsed TODO, spawn an agent using the Agent tool:

- `isolation: "worktree"` — isolated copy of the repo
- `run_in_background: true` — never block the user
- `description`: 3-5 word slug
- `prompt`: include everything below

### Agent prompt template

> **Change requested:** {parsed TODO with your added context}
>
> **Background:** This is a quick handoff from a rapid iteration session. The description is intentionally light — you need to orient yourself first:
> 1. Explore the repository to understand the codebase structure
> 2. Find the relevant code for this change
> 3. If it's a bug, try to reproduce or understand the failure mode
> 4. Make the minimal change needed
> 5. Run relevant tests if they exist
> 6. Commit with a clear message
> 7. Merge your worktree branch back into `{current branch}`: run `git checkout {current branch} && git merge {your branch} --no-edit` from the main repo, then clean up the worktree
>
> If you hit a wall (can't find the code, tests fail, merge conflicts), commit what you have and write a clear summary of what went wrong so it can be addressed manually.

## When $ARGUMENTS is "status"

Show what's been dispatched this session — which agents are still running, which completed, which had issues. Check on background agents and report.

## Example session

User: `/bark`
User: "okay so the cache list view in our full example... the help icon should be blue not gray"

You: `Dispatched: fix help icon color in cache list view → blue`

User: "and the detail page is throwing a template error, pretty sure that's from the django-tables2 upgrade"

You: `Dispatched: fix template error on cache detail page (likely django-tables2 regression)`

User: "oh also pagination is off-center on that same list"

You: `Dispatched: fix pagination alignment on cache list view`
