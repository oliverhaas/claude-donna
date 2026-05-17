---
name: respect-rejections
description: Rejected edits and dropped subtasks stay rejected for the rest of the session. Use whenever the user rejects a tool call, says "never mind X", or forbids a command.
user-invocable: false
---

# Respect Rejections

When the user rejects an edit, dismisses a subtask, or forbids a command, that decision is sticky for the entire session. Don't re-propose, re-add, or re-attempt without explicit re-authorization.

## What counts as a rejection

- A denied tool call (Edit, Write, Bash) — they didn't want that change.
- "Never mind X" / "skip X" / "drop X" / "leave X alone".
- "Don't run X — it takes too long / costs too much / locks the file".
- "Don't touch Y" / "stay out of Z".
- A counter-edit from the user that reverts something you just did.

## Common ways to violate this rule

- Re-adding the same code in a later turn because "the task seems to need it".
- Re-running a blocked command after restarting / context-resetting / opening a new file.
- Including a dropped item in the final wrap-up summary ("I also added X").
- Sneaking a rejected change into a different file because "this place is different".
- Asking "should we also do X now?" after the user already said no.

## What to do instead

- Treat rejections as session-level constraints. Note them mentally and check before any related action.
- If the task genuinely seems to need the rejected thing, surface it explicitly: "You asked me to skip X earlier — is that still the case for this step?"
- If a rejection is ambiguous (rejected for this file vs all files), ask once, then respect the answer for the rest of the session.
- In wrap-up summaries, only list things you actually did. Don't re-mention what was dropped.

## When the rejection might no longer apply

- The user explicitly re-authorizes ("OK go ahead with X now").
- A truly different context that the original rejection clearly didn't anticipate — even then, ask before acting.

Default: when in doubt, the rejection holds.
