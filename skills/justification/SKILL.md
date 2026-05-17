---
name: justification
description: Justify any new helper, wrapper, abstraction, dependency, or sibling utility before adding it. Use when writing code, designing a change, or reviewing a diff.
user-invocable: false
---

# Justification

Default is to inline or extend existing code. Anything new — a helper, a wrapper, a dataclass, a dependency, a parallel utility — has to earn its place.

## Before adding new code, ask

1. Does an existing helper, model, service, or utility already cover this? Search first.
2. Is the new thing called from more than one place? If not, inline it.
3. Would inlining read worse than the abstraction? If no, don't abstract.
4. Does the user's stated scope cover this addition? If they scoped to one call site, don't sweep the pattern into a shared utility.

## Common over-additions to avoid

- **One-call private helpers** extracted from inline code that read fine before.
- **Fake-bulk wrappers** that just loop internally — the loop at the call site is clearer.
- **Parallel helpers** alongside existing ones (`find_thing_v2` next to `find_thing`) without explaining why the original doesn't work.
- **Unexplained constants and dependencies** — `max_length=512`, a new hashing scheme, a new library — without justifying the choice.
- **Backfill/lookup helpers** when the value is already in scope at the call site.
- **Speculative abstractions** for "the next time we need this" — design for now, not hypotheticals.
- **Thin wrappers** around a shared utility that don't add behavior.

## When abstraction is justified

- Three or more real call sites with the same shape.
- A boundary you actually want to enforce (validation entrypoint, transaction wrapper, retry policy).
- Replacing a copy-pasted block whose drift has already caused bugs.

In all of these, the justification belongs in the commit message or PR description — not just in your head.

## Scope discipline

When the user scopes a change ("only do X", "just this file", "never mind Y"):
- Don't expand to adjacent files or sibling components.
- Don't re-introduce dropped items later in the same session.
- If you think the scope is wrong, surface it as a question before expanding.
