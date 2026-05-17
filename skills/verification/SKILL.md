---
name: verification
description: Show the evidence before claiming work is done. Use whenever finishing a task, pushing code, opening a PR, or making a factual claim.
user-invocable: false
---

# Verification Before Completion

Don't write "done", "fixed", "pushed", "PR opened", "ready", "complete", or "CI green" until you have the output that proves it.

## What to verify, by claim type

| Claim | Required evidence |
|-------|-------------------|
| "Test passes / bug fixed" | Test output pasted in chat; show the assertion that proved it. |
| "Pushed" / "committed" | `git log --oneline -1` after, or the push output. |
| "PR opened / ready" | `gh pr view` URL and status. |
| "CI is green" | `gh pr checks` or `gh run view` output. |
| "Dependency upgraded" | The lockfile/manifest line that changed. |
| "Refactor complete" | `grep` for the old pattern showing zero hits. |
| "UI change works" | A browser interaction or screenshot — type checks and unit tests don't verify UX. |
| "Factual claim in docs/commit/docstring" | The source: file:line, docs URL, model field. |

## When you can't verify

Say so explicitly. "I changed X but couldn't run the e2e suite" beats "Done" followed by a regression. Acceptable fallbacks:

- The smaller check you *did* run, named precisely.
- The reason the larger check is unavailable (no browser, no staging, no credentials).
- What the user would need to do to verify it themselves.

## Common verification gaps

- Declaring an MR ready before running the test that exercises the fix.
- Saying "pushed" without checking the remote actually accepted the commit.
- Asserting "CI is green" on the basis that "the change is small".
- Writing a docstring claim ("Django 5.2 supports X") from memory instead of checking.
- Refactor sweep declared done after one file, with the same pattern still in three others.

## Bug-class sweep

After fixing one instance of a bug, grep for the same pattern across the repo before declaring done. Report counts: "Fixed 3 of 3 occurrences" or "Fixed 1; 2 more in X, Y — fix or skip?". Don't leave siblings for the next session.
