---
name: commit-guidelines
description: Conventional commit message format and guidelines. Use when creating commits or writing commit messages.
user-invocable: false
---
 # Commit Message Guidelines

When creating commit messages, follow these conventions:

- Follow mostly the Conventional Commits specification (https://www.conventionalcommits.org/)
- Format: `<type>[optional scope]: <description>`
- Example: `feat(products): add endpoint for bulk price update`
- Example: `fix: correct calculation for shipping costs`
- Example: `refactor: simplify login view logic`
- Example: `docs: update setup instructions`
- Example: `perf(products): reduce N+1 queries in product list`
- Example: `ai: improved cursor rule for unit tests`
- Example: `test(merchants): add unit tests for merchant model`
- Example: `chore(deps): update django to 4.2.1`
- Keep commit messages rather brief
- No fill words
- No long descriptions
- Use type `feat` for actually user-facing feature additions
- Use type `fix` for actual bug fixes
- Use type `perf` for performance improvements
- Use type `ai` for anything regarding ai rules, instructions, or commands
- Tags and version bumps will only happen according to `feat` and `fix`, so please keep in mind to use the commit types properly
- **Do NOT add** "Co-Authored-By" or "Generated with AI" footers to commit messages, *especially* if you did not do the implementation and were just in charge of running the tests and finishing the commit workflow

## When to Commit and Push

Default to never auto-committing and never auto-pushing. After edits, stop and wait for the user.

- **Never commit** until the user explicitly says "commit", "commit and push", "ship it", or an equivalent imperative from `autonomous-execution`.
- **Never push** unless "push" appears in a user message. Fixing CI, finishing a fix, or merging an upstream rebase does NOT imply permission to push.
- **Once greenlit, execute.** Don't re-confirm. "Commit and push" is a complete instruction. See `autonomous-execution` for the trigger-phrase list.

The two failure modes (asking for confirmation after a clear imperative, and pushing without one) are mirror images. The rule: explicit imperative beats silence; silence beats implicit context.

## Clean Diffs

A commit should contain one thing.

- **No cosmetic-with-functional drift.** Don't reformat, reflow imports, or rename variables in the same commit as a behavior change. Split them.
- **No `git add .` / `git add -A`.** Stage specific paths so unrelated edits (locale files, lockfile churn, scratch notes) don't sneak in.
- **No planning artifacts.** Remove `PLAN.md`, `SPEC.md`, `*plan*.md`, `TODO.md`, scratch notes, and `.donna/` workspaces before committing. The plan lives in the PR description, not the diff.
- **No scope creep.** If the goal is "rename X to Y", change only those references. Don't refactor adjacent code "while you're in there".

Before committing, scan staged paths:

```bash
git diff --cached --name-only
```

If anything in that list doesn't belong in the one-line commit message, unstage it.

---
