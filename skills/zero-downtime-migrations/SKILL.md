---
name: zero-downtime-migrations
description: Schema migration strategies for zero-downtime deploys on PostgreSQL. Use when adding/removing columns, indexes, constraints, or foreign keys that must not lock production tables.
user-invocable: false
---

# Zero-Downtime Migrations

Schema changes on live PostgreSQL tables can lock out concurrent reads/writes for seconds to minutes. This guide covers safe patterns for each operation type.

See also: `django-data-migrations` for backfilling data alongside schema changes.

## Core Tools

**django-pg-zero-downtime-migrations** — wraps Django migrations to use safe Postgres DDL:

```python
# settings.py
INSTALLED_APPS = [..., "django_zero_downtime_migrations"]

ZERO_DOWNTIME_MIGRATIONS_RAISE_FOR_UNSAFE = True  # Fail fast in CI
ZERO_DOWNTIME_MIGRATIONS_LOCK_TIMEOUT = "2s"       # Max time to wait for a lock
ZERO_DOWNTIME_MIGRATIONS_STATEMENT_TIMEOUT = "2s"  # Max time per DDL statement
```

**django-syzygy** — splits migrations into pre-deploy and post-deploy phases:

```python
# settings.py
INSTALLED_APPS = [..., "syzygy"]

# Run before deploy (safe DDL only)
# python manage.py migrate --stage pre_deploy

# Run after deploy (data cleanup, constraint validation)
# python manage.py migrate --stage post_deploy
```

## Safe vs Unsafe Operations

| Operation | Safe? | Notes |
|---|---|---|
| Add nullable column | Yes | No default = instant |
| Add column with DB default (Postgres 11+) | Yes | No table rewrite |
| Add column with Django default + null | Yes | Use two phases for NOT NULL |
| Remove column | No | Requires app code removed first (expand-contract) |
| Rename column | No | Use two phases |
| Add index | No | Use `CONCURRENTLY` |
| Add unique index | No | Use `CONCURRENTLY` then constraint |
| Add CHECK constraint (NOT VALID) | Yes | Validate separately post-deploy |
| Add FK (NOT VALID) | Yes | Validate separately post-deploy |
| Change column type | No | Often requires rewrite |
| Add NOT NULL without default | No | Requires backfill first |

## Column Addition

### Nullable column (simplest)

```python
# One migration, instant on Postgres
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name="order",
            name="notes",
            field=models.TextField(null=True, blank=True),
        ),
    ]
```

### Column with default (Postgres 11+)

Postgres 11+ stores the default as metadata — no table rewrite, instant:

```python
# settings.py: ZERO_DOWNTIME_MIGRATIONS_KEEP_DEFAULT = True
# This emits DEFAULT in the DDL instead of backfilling afterward

class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name="order",
            name="status",
            field=models.CharField(max_length=20, default="pending"),
        ),
    ]
```

django-pg-zero-downtime-migrations handles this correctly when `KEEP_DEFAULT` is set. Without it, Django would add the column, backfill all rows (locks table), then drop the default — unsafe on large tables.

## NOT NULL Constraint Addition

Never add `NOT NULL` without a default on a table with existing rows. Use three phases:

**Phase 1 — pre-deploy:** Add nullable column

```python
migrations.AddField(
    model_name="order",
    name="region",
    field=models.CharField(max_length=50, null=True, blank=True),
)
```

**Phase 2 — data migration (post-deploy of phase 1):** Backfill existing rows

```python
from syzygy import Stage

class Migration(migrations.Migration):
    stage = Stage.POST_DEPLOY

    operations = [
        migrations.RunPython(
            backfill_region,
            migrations.RunPython.noop,
        ),
    ]


def backfill_region(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    Order.objects.filter(region__isnull=True).update(region="unknown")
```

**Phase 3 — pre-deploy of next release:** Add NOT VALID constraint, then validate

```python
# Add constraint NOT VALID (doesn't scan existing rows)
migrations.AddConstraint(
    model_name="order",
    constraint=models.CheckConstraint(
        check=models.Q(region__isnull=False),
        name="order_region_not_null",
        violation_error_message="region is required",
    ),
)
# Then in a second operation or next post-deploy migration:
# VALIDATE CONSTRAINT (scans rows, no lock)
```

Alternatively with django-pg-zero-downtime-migrations, `AlterField` to `null=False` is made safe automatically by emitting `NOT VALID` + deferred `VALIDATE`.

## Column Removal (Expand-Contract)

Never drop a column while the app still references it. Follow expand-contract:

**Phase 1 — pre-deploy:** Stop reading/writing the column in application code. Remove field from model but keep the DB column.

Django ignores columns that exist in DB but not in the model, so removing the model field first is safe.

**Phase 2 — post-deploy:** Drop the column once the old code is fully gone:

```python
from syzygy import Stage

class Migration(migrations.Migration):
    stage = Stage.POST_DEPLOY

    operations = [
        migrations.RemoveField(model_name="order", name="legacy_notes"),
    ]
```

## Column Rename

Never rename directly — it breaks running app instances. Use expand-contract:

1. Add new column (nullable)
2. Deploy app writing to both old and new column
3. Backfill new column from old
4. Deploy app reading from new column only
5. Drop old column

```python
# Step 1
migrations.AddField(model_name="product", name="slug_new", field=models.SlugField(null=True))

# Step 3 - data migration
def copy_slug(apps, schema_editor):
    Product = apps.get_model("catalogue", "Product")
    Product.objects.update(slug_new=models.F("slug_old"))

# Step 5 (post-deploy of step 4)
migrations.RemoveField(model_name="product", name="slug_old")
```

## Index Creation

Always use `CONCURRENTLY`. Django's `db_index=True` does not do this by default.

```python
# Correct: concurrent index creation
from django.db import migrations
from django.contrib.postgres.operations import AddIndexConcurrently

class Migration(migrations.Migration):
    atomic = False  # Required for CONCURRENTLY

    operations = [
        AddIndexConcurrently(
            model_name="order",
            index=models.Index(fields=["created_at"], name="order_created_at_idx"),
        ),
    ]
```

`CONCURRENTLY` cannot run inside a transaction — set `atomic = False`.

Similarly for removal:

```python
from django.contrib.postgres.operations import RemoveIndexConcurrently

class Migration(migrations.Migration):
    atomic = False

    operations = [
        RemoveIndexConcurrently(model_name="order", name="order_created_at_idx"),
    ]
```

### Unique index

Never use `unique=True` on a new field if adding it via a single migration on a large table. Use:

1. `AddIndexConcurrently` with a unique index to build it safely
2. Then add the `UniqueConstraint` using the existing index (Postgres `USING INDEX`)

```python
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db.models import UniqueConstraint

class Migration(migrations.Migration):
    atomic = False

    operations = [
        AddIndexConcurrently(
            model_name="order",
            index=models.Index(
                fields=["reference"],
                name="order_reference_uniq",
            ),
        ),
    ]

# Separate atomic migration after the concurrent index build:
class Migration(migrations.Migration):
    operations = [
        migrations.AddConstraint(
            model_name="order",
            constraint=UniqueConstraint(fields=["reference"], name="order_reference_unique"),
        ),
    ]
```

## Foreign Key Addition

Adding a FK with `VALIDATE` on a large table takes a full sequential scan under `ShareRowExclusiveLock`. Use `NOT VALID` + deferred validate:

```python
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="product",
            field=models.ForeignKey(
                "catalogue.Product",
                on_delete=models.PROTECT,
                null=True,
            ),
        ),
    ]
```

django-pg-zero-downtime-migrations emits `ADD CONSTRAINT ... NOT VALID` automatically for FK additions when configured. The validation pass is deferred to a post-deploy migration:

```python
from syzygy import Stage
from django_zero_downtime_migrations.operations import ValidateConstraint

class Migration(migrations.Migration):
    stage = Stage.POST_DEPLOY

    operations = [
        ValidateConstraint(
            model_name="orderitem",
            name="orderitem_product_id_fk",
        ),
    ]
```

## CHECK Constraint Addition

Same pattern — add `NOT VALID`, validate post-deploy:

```python
# Pre-deploy: add without validation
class Migration(migrations.Migration):
    operations = [
        migrations.AddConstraint(
            model_name="order",
            constraint=models.CheckConstraint(
                check=models.Q(total__gte=0),
                name="order_total_non_negative",
            ),
        ),
    ]
```

With `ZERO_DOWNTIME_MIGRATIONS_RAISE_FOR_UNSAFE = True`, this is emitted as `NOT VALID`. Validate post-deploy:

```python
from syzygy import Stage
from django_zero_downtime_migrations.operations import ValidateConstraint

class Migration(migrations.Migration):
    stage = Stage.POST_DEPLOY

    operations = [
        ValidateConstraint(model_name="order", name="order_total_non_negative"),
    ]
```

## Enum / TextChoices Changes

Model-level choices are Django metadata only — no DDL. Safe to add values.

Removing or renaming a choice value requires a data migration to update existing rows first (see `django-data-migrations`). The schema change (new choice) can deploy before the data backfill completes; old app instances simply won't render the new value.

For PostgreSQL native ENUM types (uncommon in Django): avoid them. Postgres ENUM changes require DDL that is hard to do safely.

## django-syzygy Stage Reference

```python
from syzygy import Stage

# Options:
Stage.PRE_DEPLOY   # Must run before new code goes live (safe DDL, additive changes)
Stage.POST_DEPLOY  # Must run after new code is live (data backfills, constraint validate, column drops)
```

Set `stage` on the `Migration` class. The management command enforces ordering:

```bash
# CI/deploy pipeline
python manage.py migrate --stage pre_deploy
# ... deploy new app version ...
python manage.py migrate --stage post_deploy
```

Migrations without a `stage` attribute run in the default pass.

## Testing Migrations

```python
# tests/test_migrations.py
import pytest
from django.test import TestCase
from django.db import connection


@pytest.mark.django_db
def test_no_missing_migrations():
    """Fail if model changes haven't been captured in a migration."""
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    call_command("makemigrations", "--check", "--dry-run", stdout=out)


@pytest.mark.django_db
def test_no_unapplied_migrations():
    """Check no unapplied migrations exist."""
    from django.db.migrations.executor import MigrationExecutor
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    assert plan == [], f"Unapplied migrations: {[m.name for m, _ in plan]}"
```

For testing migration correctness in isolation, use `MigrationExecutor` to roll forward and back:

```python
@pytest.mark.django_db(transaction=True)
def test_backfill_migration(transactional_db):
    from django.db.migrations.executor import MigrationExecutor
    from django.db import connection

    executor = MigrationExecutor(connection)
    # Roll back to before the migration
    executor.migrate([("orders", "0041_add_region")])
    # Insert data in old state
    ...
    # Roll forward
    executor.migrate([("orders", "0042_backfill_region")])
    # Assert new state
    ...
```

## Checklist

Before merging a migration:

- [ ] No `AddField` with `null=False` and no DB/Django default on non-empty table
- [ ] No plain `AddIndex` — use `AddIndexConcurrently` (with `atomic = False`)
- [ ] No `AddConstraint` with immediate validation on large table
- [ ] FK additions use `NOT VALID` + deferred `ValidateConstraint`
- [ ] Column drops are in `POST_DEPLOY` stage, app code already removed the field
- [ ] Data migrations use `apps.get_model()`, not direct model imports
- [ ] `ZERO_DOWNTIME_MIGRATIONS_RAISE_FOR_UNSAFE = True` passes in CI
- [ ] `makemigrations --check` passes (no drift)

---
