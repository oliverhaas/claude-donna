---
name: pr
description: Complete pull request workflow: review changes, create branch, commit, push, and create PR.
disable-model-invocation: true
---

Complete pull request workflow: review changes, create branch, commit, push, and create PR.

## Step 1: Review Changes
Review what you've implemented to ensure completeness and think of a good branch name:

```bash
git status
git diff
git log --oneline -5
```

## Step 2: Create Branch
Create appropriately named branch. The prefix should match the commit type (e.g. `feat/`, `fix/`, `perf/`, `refactor/`, etc.).

**With ticket:**
```bash
git checkout -b <type>/PROJ-XXXX-descriptive-name
```

**Without ticket:**
```bash
git checkout -b <type>/descriptive-name
```

## Step 3: Commit Changes
Add and commit your changes (pre-commit hooks will run automatically):

```bash
git add .
git commit -m "<type>: descriptive commit message"
```

## Step 4: Push & Create PR (as Draft)
Push and create pull request as **draft** so the human can review before marking ready:

**With ticket:**
```bash
git push --set-upstream origin <branch>
gh pr create --draft --title "Draft: <type>(PROJ-XXXX): descriptive title" --body "Closes PROJ-XXXX"
```

**Without ticket:**
```bash
git push --set-upstream origin <branch>
gh pr create --draft --title "Draft: <type>: descriptive title" --body ""
```

**PR description must be super short, one sentence max.** No long descriptions, bullet lists, or summaries.

## Step 5: Update Ticket (if applicable)
If there is a ticket associated with this work, check its description. If it has no description or very little (e.g., just a link to an error log):
- Add 2-3 concise sentences explaining the problem and the attempted fix.
- Write from the current point in time.

## Step 6: Check CI (after 10 minutes)
Wait 10 minutes, then check if the CI checks passed:

```bash
sleep 600 && gh pr checks
```

If CI failed: check the output, fix issues, commit, push, and wait for CI again. If the user interrupts before the check, that's fine. Skip this step.


---
