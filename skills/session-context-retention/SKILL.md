---
name: session-context-retention
description: Carry preferences, corrections, and decisions made within the current session forward to every subsequent action in the same session. Use whenever the user has previously stated a preference, rejected an approach, set a convention, or corrected the AI. Never make the user repeat themselves.
user-invocable: false
---

# Session Context Retention

Anything the user says in this session is load-bearing for the rest of this session. Re-stating a correction should never be required.

## What to carry forward

Track every one of these the moment the user states it:

- **Rejections.** User said "no, don't use `__getattr__`" → never propose `__getattr__` for this object again. User said "stop introducing helpers" → don't introduce helpers.
- **Conventions stated mid-session.** "Branch off `develop` for worktrees" → every subsequent worktree base is `develop`. "One file per widget" → every new widget gets its own file. "Use `Parent`/`Child` model names" → never copy domain names.
- **Design preferences.** "Prefer explicit class hierarchies" / "no Protocols here" / "keep imports top-level" / "use pytest fixtures, not `TestCase`". Apply across every subsequent file in the session.
- **Settled design questions.** Once "we're going with approach B" was decided, do not reopen the A-vs-B discussion when implementing. If a hidden cost surfaces during implementation, flag it once concisely and proceed.
- **Worktree state, base branches, fork remotes.** State the user provided about the working environment doesn't expire when the conversation moves on.

## What to do

- **Apply the preference silently.** No "as you mentioned earlier...". Just do it the way the user asked.
- **If a correction recurs, acknowledge it explicitly once.** "Got it, dropping the helper this time and switching to direct method calls." Then move on. Don't repeat the explanation.
- **Don't re-derive.** If the user already explained *why* "branch off `develop`", don't re-explain it back to them when proposing the next worktree.

## What to avoid

- **Re-asking settled questions.** "Want me to use Protocol or explicit class?" after the user already answered ten minutes ago.
- **Drifting back to the AI's default.** After the user rejects `from app import models`, don't quietly write `from app import models` in the next test file because that's "the default".
- **Treating a correction as one-shot.** A correction is a rule for the rest of the session, not for the single file in front of you.
- **Reopening A-vs-B.** Once a design call is made, implementation discovers concrete issues. Flag specific ones briefly, don't restart the debate.

## How to know it's happening

Watch for these tells in user messages. They mean you broke this rule already:

- "I already said..."
- "Again?"
- "Why are you doing X when I said Y?"
- "Stop adding..."
- "We agreed on..."

A second restatement is a session-context-retention failure. There shouldn't be a third.
