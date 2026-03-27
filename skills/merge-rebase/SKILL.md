---
name: merge-rebase
description: Merge the latest origin/main into the current branch.
disable-model-invocation: true
---

# Merge Rebase

Merge the latest origin/main into the current branch.

## 1. Fetch & Merge

```bash
git fetch origin
git merge origin/main
```

## 2. Resolve Conflicts

If there are merge conflicts:
1. Understand the goal of the current branch and the changes in origin/main. Do not accidentally revert intentional changes or break logic from either side.
2. Identify conflicting files from the merge output
3. Read each conflicting file and resolve conflicts
4. **Migration conflicts:** If migrations have a conflict, redo them from scratch instead of using `makemigrations --merge`. Delete the conflicting migration(s) from this branch and regenerate them so they slot in after the latest migration from main. If they are custom (data) migrations, manually modify them to reference the correct new dependency.
5. Stage resolved files: `git add <file>`
6. Complete the merge: `git commit`

If there are no conflicts, skip this step.

## 3. Push

```bash
git push
```


---
