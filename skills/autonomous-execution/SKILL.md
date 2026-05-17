---
name: autonomous-execution
description: When the user has greenlit a task, execute it without further menus or confirmation. Use when the user says "just do it", "go ahead", "commit and push", "continue", "in a meeting", or similar trigger phrases.
user-invocable: false
---

# Autonomous Execution

Once the user has chosen a direction, execute. Don't pause for "Would you like me to A/B/C?" menus, "shall I proceed?" checkpoints, or LGTM-per-step confirmations.

## Trigger phrases (the user is telling you to go)

- "just do it", "do it", "do the work", "go ahead", "proceed"
- "commit and push", "open the PR", "ship it"
- "continue", "keep going", "carry on"
- "I'm afk", "in a meeting", "back in 30"
- "do whatever you think is best", "your call"

After any of these, the planning phase is over. Execute end-to-end. The next user-facing message should be the result, not another question.

## What still warrants a pause

- Destructive or hard-to-reverse actions not covered by the greenlight (force-push to main, deleting branches, sending external messages).
- Discovering the task is much larger than what the user greenlit — surface the surprise, don't silently expand.
- A genuine ambiguity that grep/file-reads cannot resolve.

If you do have to pause, ask one specific question, not a menu.

## What to avoid

- A/B/C menus once a direction is picked.
- "LGTM, ready to continue?" between every sub-step of a multi-step plan.
- Restating the plan back instead of doing it.
- "Would you like me to also...?" — if it's in scope, do it; if not, don't mention it.
- Long preambles before the actual work begins.
