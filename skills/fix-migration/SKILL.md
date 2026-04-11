---
name: fix-migration
description: Fix broken, conflicting, or problematic Django migrations.
user-invocable: true
---

# Fix Migration

Fix broken, conflicting, or problematic Django migrations.

## 0. What's Wrong?

Common migration problems:
- **Conflicting migrations** - two migrations with the same dependency (branch merge)
- **Broken migration** - syntax error, missing dependency, or references deleted model
- **Migration won't apply** - fails on `migrate` with DB errors
- **Accidental migration** - generated migration that shouldn't exist

## 1. Diagnose

```bash
# Check current migration state
uv run python manage.py showmigrations | grep -E '\[ \]|ERRORS'

# Check for conflicts
uv run python manage.py makemigrations --check --dry-run

# See which migrations are applied
uv run python manage.py showmigrations app_name
```

## 2. Fix by Problem Type

### Conflicting migrations (most common after merging branches)

```bash
# Regenerate the merge migration
uv run python manage.py makemigrations --merge
```

If the conflicting migrations touch the same fields, the auto-merge may not work. In that case:
1. Delete the conflicting migration from your branch
2. Regenerate: `uv run python manage.py makemigrations`
3. Verify: `uv run python manage.py migrate --plan`

### Broken migration file

1. Read the traceback to find the exact error
2. Fix the migration file directly if it's a simple syntax/reference issue
3. If the migration is hopelessly broken and unapplied, delete it and regenerate

### Migration won't apply (DB state mismatch)

```bash
# See what SQL it would run
uv run python manage.py sqlmigrate app_name 0042_migration_name

# If the column/table already exists, fake it
uv run python manage.py migrate app_name 0042_migration_name --fake
```

Only use `--fake` when you're certain the DB state already matches what the migration would do.

### Accidental migration (shouldn't exist)

If unapplied: just delete the file.

If already applied:
```bash
# Revert to the previous migration
uv run python manage.py migrate app_name 0041_previous_migration

# Then delete the bad migration file
```

## 3. Verify

```bash
# Confirm no pending migrations
uv run python manage.py makemigrations --check --dry-run

# Confirm migrate runs clean
uv run python manage.py migrate --plan

# Run tests
uv run pytest -x
```

## 4. Commit

```bash
git add -A && git commit -m "fix: resolve migration conflict in app_name"
```
