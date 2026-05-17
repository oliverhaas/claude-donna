---
name: merge-rebase
description: Merge the latest target branch into the current branch.
user-invocable: true
---

# Merge Rebase

Merge the latest target branch into the current branch. The target branch is the PR's base, which is not always `main` (release branches, stacked PRs).

## 1. Determine the Target Branch

If the current branch has an open PR, use its base ref:

```bash
gh pr view --json baseRefName --jq '.baseRefName'
```

If there is no PR, default to `main` (or ask the user if working in a repo with a different default). Use the result as `{target_branch}` below.

## 2. Sync the Current Branch with Its Remote

```bash
git fetch origin "$(git rev-parse --abbrev-ref HEAD)"
```

Then compare local to the remote tip:

- **Local is behind:** fast-forward local before merging (`git merge --ff-only @{u}`). Otherwise your merge will be redundant and may miss fix-up commits that already exist on the remote (e.g. migration renumbering after a previous main-merge from another worktree).
- **Diverged:** stop and investigate. Someone else (or you in another worktree) has pushed work you don't have. Reconcile before merging the target branch on top.
- **Local is ahead or equal:** safe to proceed.

## 3. Fetch & Merge

```bash
git fetch origin {target_branch}
git merge origin/{target_branch}
```

## 4. Resolve Conflicts

If there are merge conflicts:

1. Understand the goal of the current branch and the changes in the target branch. Do not accidentally revert intentional changes or break logic from either side.
2. Identify conflicting files from the merge output.
3. Read each conflicting file and resolve conflicts.
4. **Migration conflicts:** If migrations have a conflict, redo them from scratch instead of using `makemigrations --merge`. Delete the conflicting migration(s) from this branch and regenerate them so they slot in after the latest migration from the target branch. If they are custom (data) migrations, manually modify them to reference the correct new dependency.
5. Stage resolved files: `git add <file>`.
6. Complete the merge: `git commit`.

If there are no conflicts, skip this step.

## 5. Double-check Incoming Changes

Skim the diff that came in from the target branch even if there were no conflicts. Two things to look for:

- **Conflicts you didn't notice.** Auto-merge can produce syntactically valid but semantically broken code (e.g. a refactor on one side and a touch on the same area from the other).
- **Patterns to bring forward.** A refactor branch may have absorbed changes that don't follow the new pattern. Convert them now so the merge doesn't ship a regression.

## 6. Push

```bash
git push
```
