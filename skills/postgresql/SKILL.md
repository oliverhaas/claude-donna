---
name: postgresql
description: PostgreSQL-specific patterns for Django: constraints, triggers, indexes, advisory locks, CTEs, window functions, JSONB, partitioning, django-pgtrigger, django-pg-zero-downtime-migrations, and PG-specific fields. Use when writing or reviewing PostgreSQL-specific database code in Django.
user-invocable: false
---

# PostgreSQL Patterns for Django

PostgreSQL-specific capabilities beyond what generic Django ORM covers. Cross-reference `django-orm-queries` for general query optimization and `django-data-migrations` for safely backfilling data when adding constraints.

---

## Constraints

### CHECK Constraints

Enforce invariants at the DB level — they fire even on raw SQL and bulk operations that bypass Django.

```python
from django.db import models
from django.db.models import CheckConstraint, Q

class Order(models.Model):
    quantity = models.IntegerField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)

    class Meta:
        constraints = [
            CheckConstraint(condition=Q(quantity__gte=0), name="order_quantity_non_negative"),
            CheckConstraint(condition=Q(total__gte=0), name="order_total_non_negative"),
            CheckConstraint(
                condition=Q(status__in=["pending", "paid", "cancelled"]),
                name="order_status_valid",
            ),
        ]
```

Always backfill violating rows before adding a CHECK constraint (see `django-data-migrations`).

### Partial Unique Constraints

Unique among a filtered subset of rows — e.g., only one active record per user.

```python
from django.db.models import UniqueConstraint

class Subscription(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    status = models.CharField(max_length=20)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["user"],
                condition=Q(status="active"),
                name="subscription_one_active_per_user",
            )
        ]
```

Generates `CREATE UNIQUE INDEX ... WHERE status = 'active'` — no nullability tricks needed.

### EXCLUDE Constraints

Prevent overlapping ranges. Requires `btree_gist` extension.

```python
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators
from django.db.models import DateRangeField

class Booking(models.Model):
    resource = models.ForeignKey("Resource", on_delete=models.CASCADE)
    period = DateRangeField()

    class Meta:
        constraints = [
            ExclusionConstraint(
                name="booking_no_overlap",
                expressions=[
                    ("resource", RangeOperators.EQUAL),
                    ("period", RangeOperators.OVERLAPS),
                ],
            )
        ]
```

Enable the extension in a migration first:

```python
from django.contrib.postgres.operations import BtreeGistExtension

class Migration(migrations.Migration):
    operations = [BtreeGistExtension()]
```

### Cross-Table Constraints via Triggers

PostgreSQL constraints can't span tables. Use triggers for cross-table invariants (e.g., "a line item's product must belong to the same merchant as its order"). See the **Triggers** section below.

---

## Triggers and Trigger Functions

Use `django-pgtrigger` to define triggers as Python alongside your models. Triggers fire even on bulk SQL that bypasses Django.

### Installation

```python
# settings.py
INSTALLED_APPS = [
    ...
    "pgtrigger",
]
```

### Basic Trigger: Soft Delete

```python
import pgtrigger
from django.db import models

@pgtrigger.register(
    pgtrigger.SoftDelete(
        name="soft_delete",
        field="deleted_at",
    )
)
class Document(models.Model):
    title = models.CharField(max_length=200)
    deleted_at = models.DateTimeField(null=True, blank=True)
```

### Custom Trigger: Cross-Table Constraint

```python
import pgtrigger

@pgtrigger.register(
    pgtrigger.Trigger(
        name="check_product_merchant",
        operation=pgtrigger.Insert | pgtrigger.Update,
        when=pgtrigger.Before,
        func="""
            IF NEW.product_id IS NOT NULL THEN
                IF NOT EXISTS (
                    SELECT 1 FROM products_product p
                    JOIN orders_order o ON o.id = NEW.order_id
                    WHERE p.id = NEW.product_id
                      AND p.merchant_id = o.merchant_id
                ) THEN
                    RAISE EXCEPTION 'Product merchant does not match order merchant';
                END IF;
            END IF;
            RETURN NEW;
        """,
    )
)
class OrderItem(models.Model):
    order = models.ForeignKey("Order", on_delete=models.CASCADE)
    product = models.ForeignKey("Product", on_delete=models.CASCADE)
    quantity = models.IntegerField()
```

### Trigger: Protect Against Deletes

```python
@pgtrigger.register(
    pgtrigger.Protect(
        name="protect_paid_orders",
        operation=pgtrigger.Delete,
        condition=pgtrigger.Q(old__status="paid"),
    )
)
class Order(models.Model):
    status = models.CharField(max_length=20)
```

### Managing Triggers

```bash
# Install all triggers onto the DB
uv run python manage.py pgtrigger install

# Check trigger status
uv run python manage.py pgtrigger ls

# Temporarily disable (useful in tests or data migrations)
with pgtrigger.ignore("myapp.Order:protect_paid_orders"):
    Order.objects.filter(status="paid").delete()
```

---

## Index Types

Choose based on the query pattern, not just column type.

| Index | Use For | Django |
|-------|---------|--------|
| B-tree (default) | `=`, `<`, `>`, `BETWEEN`, `ORDER BY`, `LIKE 'foo%'` | `db_index=True` or `models.Index` |
| GIN | `@>`, `?`, `?|`, `?&` on JSONB; full-text search; arrays | `GinIndex` |
| GiST | Geometric types, range overlap (`&&`), full-text search with ranking | `GistIndex` |
| BRIN | Append-only large tables where physical order correlates with query range (e.g. `created_at` on an insert-only events table) | `BrinIndex` |

```python
from django.contrib.postgres.indexes import GinIndex, GistIndex, BrinIndex
from django.db import models

class Event(models.Model):
    metadata = models.JSONField()
    tags = models.ArrayField(models.CharField(max_length=50), default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # GIN: fast JSONB key/value lookups
            GinIndex(fields=["metadata"], name="event_metadata_gin"),
            # GIN: fast array containment queries
            GinIndex(fields=["tags"], name="event_tags_gin"),
            # BRIN: very small index on monotonically increasing column
            BrinIndex(fields=["created_at"], name="event_created_at_brin"),
        ]
```

**B-tree partial index** — small, covers only the rows you query:

```python
from django.db.models import Index

class Meta:
    indexes = [
        Index(
            fields=["user", "status"],
            condition=Q(status="pending"),
            name="order_pending_by_user",
        )
    ]
```

**GiST for range overlap:**

```python
from django.contrib.postgres.indexes import GistIndex

class Meta:
    indexes = [
        GistIndex(fields=["period"], name="booking_period_gist"),
    ]
```

---

## Advisory Locks

Application-level locks that don't touch table rows. Use for distributed mutual exclusion (e.g., "only one worker processes account X at a time").

```python
from django.db import connection

def acquire_advisory_lock(key: int) -> bool:
    """Non-blocking. Returns True if acquired."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [key])
        return cursor.fetchone()[0]

def release_advisory_lock(key: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_unlock(%s)", [key])


from contextlib import contextmanager

@contextmanager
def advisory_lock(key: int):
    """Blocking context manager. Acquires lock, releases on exit."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_lock(%s)", [key])
    try:
        yield
    finally:
        release_advisory_lock(key)
```

Usage in a Celery task:

```python
ACCOUNT_LOCK_BASE = 1_000_000  # Namespace to avoid collisions

def process_account(account_id: int) -> None:
    lock_key = ACCOUNT_LOCK_BASE + account_id
    with advisory_lock(lock_key):
        # Only one worker holds this at a time
        _do_work(account_id)
```

Session-level locks (above) auto-release when the DB connection closes. For transaction-scoped locks use `pg_advisory_xact_lock` / `pg_try_advisory_xact_lock` — released at `COMMIT`/`ROLLBACK`.

---

## CTEs and Window Functions

### CTEs

Django ORM doesn't natively support `WITH` CTEs (as of Django 6.x). Use `django-cte` or raw SQL.

```python
from django.db import connection

def get_top3_products_by_category() -> list[dict]:
    sql = """
        WITH ranked AS (
            SELECT
                id,
                name,
                category_id,
                price,
                ROW_NUMBER() OVER (
                    PARTITION BY category_id
                    ORDER BY price DESC
                ) AS rank
            FROM products_product
            WHERE status = 'active'
        )
        SELECT id, name, category_id, price, rank
        FROM ranked
        WHERE rank <= 3
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
```

### Window Functions in Django ORM

Django supports `Window` expressions natively:

```python
from django.db.models import F, Sum, Window
from django.db.models.functions import Rank, Lag

# Rank products by price within each category
Product.objects.annotate(
    price_rank=Window(
        expression=Rank(),
        partition_by=[F("category")],
        order_by=F("price").desc(),
    )
)

# Running total per merchant
Order.objects.annotate(
    running_total=Window(
        expression=Sum("total"),
        partition_by=[F("merchant")],
        order_by=F("created_at").asc(),
    )
)

# Previous row value
Order.objects.annotate(
    prev_total=Window(
        expression=Lag("total", default=0),
        partition_by=[F("merchant")],
        order_by=F("created_at").asc(),
    )
)
```

**Filtering on window results requires a subquery** — SQL doesn't allow `WHERE` on window functions:

```python
# Filter to top-3 per category using a subquery
top3_ids = (
    Product.objects.filter(category=OuterRef("category"))
    .annotate(rank=Window(expression=Rank(), order_by=F("price").desc()))
    .order_by("rank")
    .values("id")[:3]
)
```

Or use a raw SQL CTE as shown above.

---

## JSONB Patterns

### Django Fields and Lookups

```python
from django.db import models

class Product(models.Model):
    metadata = models.JSONField(default=dict)
```

```python
# Key existence
Product.objects.filter(metadata__has_key="color")
Product.objects.filter(metadata__has_keys=["color", "size"])
Product.objects.filter(metadata__has_any_keys=["color", "material"])

# Key/value path
Product.objects.filter(metadata__color="red")
Product.objects.filter(metadata__dimensions__width__gte=10)

# Containment: metadata contains this dict
Product.objects.filter(metadata__contains={"brand": "acme"})

# Contained by
Product.objects.filter(metadata__contained_by={"color": "red", "size": "L"})
```

### GIN Index for JSONB

```python
from django.contrib.postgres.indexes import GinIndex

class Meta:
    indexes = [
        GinIndex(fields=["metadata"], name="product_metadata_gin"),
    ]
```

### Updating Nested JSONB Atomically

```python
from django.db.models import F, Func, Value

# Bad: fetches to Python, overwrites entire column
product = Product.objects.get(id=pk)
product.metadata["color"] = "blue"
product.save()

# Good: atomic jsonb_set at DB level
Product.objects.filter(id=pk).update(
    metadata=Func(
        F("metadata"),
        Value("color"),
        Value("blue"),
        function="jsonb_set",
        output_field=models.JSONField(),
    )
)
```

---

## Partitioning

Partition large tables to improve query performance and maintenance (e.g., archiving old partitions by detaching them).

### Range Partitioning (Most Common)

Django doesn't manage partitioning natively — use a raw migration.

```python
from django.db import migrations

class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE events_event (
                    id bigserial,
                    created_at timestamptz NOT NULL,
                    payload jsonb NOT NULL
                ) PARTITION BY RANGE (created_at);

                CREATE TABLE events_event_2024
                    PARTITION OF events_event
                    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

                CREATE TABLE events_event_2025
                    PARTITION OF events_event
                    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
            """,
            reverse_sql="DROP TABLE IF EXISTS events_event CASCADE;",
        )
    ]
```

Key constraints:
- Primary key and unique constraints must include the partition key column.
- Indexes defined on the parent are automatically created on each child partition.
- `INSERT` routes automatically; `SELECT` uses partition pruning when `WHERE` includes the partition key.

### Create New Partitions Ahead of Time

```python
from datetime import date, timedelta
from django.db import connection

def create_next_month_partition() -> None:
    today = date.today()
    next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    month_after = (next_month + timedelta(days=32)).replace(day=1)
    partition_name = f"events_event_{next_month.strftime('%Y_%m')}"
    with connection.cursor() as cursor:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {partition_name}
                PARTITION OF events_event
                FOR VALUES FROM ('{next_month}') TO ('{month_after}');
        """)
```

Call from a periodic Celery task (e.g., monthly).

---

## Safe Schema Changes: django-pg-zero-downtime-migrations

`django-pg-zero-downtime-migrations` rewrites dangerous DDL into lock-safe equivalents. Pair with `django-syzygy` for staged (pre/post-deploy) migrations.

### Setup

```python
# settings.py
DATABASES = {
    "default": {
        "ENGINE": "django_zero_downtime_migrations.backends.postgresql",
        ...
    }
}
```

### What It Handles Automatically

- `ADD COLUMN NOT NULL DEFAULT` → adds column nullable, sets default, adds NOT NULL constraint
- `CREATE INDEX` → rewritten to `CREATE INDEX CONCURRENTLY`
- `DROP INDEX` → rewritten to `DROP INDEX CONCURRENTLY`
- `ADD CONSTRAINT` → `ADD CONSTRAINT ... NOT VALID` + `VALIDATE CONSTRAINT`

### What Still Requires Care

**Adding a NOT NULL column without a server-side default:** three-step deploy.

```python
# Step 1 (pre-deploy): add nullable column
migrations.AddField(
    model_name="product",
    name="slug",
    field=models.SlugField(null=True, blank=True),
)

# Step 2: data migration — backfill slug for all existing rows
# Use django-syzygy Stage.POST_DEPLOY; see django-data-migrations skill

# Step 3 (post-deploy): tighten to NOT NULL
migrations.AlterField(
    model_name="product",
    name="slug",
    field=models.SlugField(null=False),
)
```

**Renaming a column:** never rename in a single deploy — it breaks running code. Add the new column, dual-write, backfill, switch reads, drop the old column across multiple deploys.

---

## PostgreSQL-Specific Django Fields and Lookups

### ArrayField

```python
from django.contrib.postgres.fields import ArrayField

class Post(models.Model):
    tags = ArrayField(models.CharField(max_length=50), default=list, blank=True)
```

```python
# All of these tags present
Post.objects.filter(tags__contains=["python", "django"])

# Any of these tags present
Post.objects.filter(tags__overlap=["python", "rust"])

# Array length
Post.objects.filter(tags__len__gte=3)
```

Index with GIN for containment/overlap queries:

```python
class Meta:
    indexes = [GinIndex(fields=["tags"], name="post_tags_gin")]
```

### HStoreField

Key-value pairs where both keys and values are strings.

```python
from django.contrib.postgres.fields import HStoreField

class Config(models.Model):
    settings = HStoreField(default=dict)
```

```python
Config.objects.filter(settings__has_key="theme")
Config.objects.filter(settings__contains={"theme": "dark"})
```

Requires `hstore` extension in a migration:

```python
from django.contrib.postgres.operations import HStoreExtension

class Migration(migrations.Migration):
    operations = [HStoreExtension()]
```

### DateRangeField / DateTimeRangeField

```python
from django.contrib.postgres.fields import DateRangeField

class Campaign(models.Model):
    active_period = DateRangeField()
```

```python
from datetime import date
from django.db.backends.postgresql.psycopg_any import DateRange

Campaign.objects.create(active_period=DateRange(date(2025, 1, 1), date(2025, 12, 31)))

# Overlaps with a date range
Campaign.objects.filter(active_period__overlap=DateRange(date.today(), date.today()))

# Contains a specific date
Campaign.objects.filter(active_period__contains=date.today())
```

### Full-Text Search

```python
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

qs = Product.objects.annotate(
    search=SearchVector("name", "description", config="english"),
).filter(search=SearchQuery("laptop keyboard", config="english"))

# With ranking
qs = Product.objects.annotate(
    rank=SearchRank(
        SearchVector("name", config="english"),
        SearchQuery("laptop", config="english"),
    ),
).filter(rank__gte=0.1).order_by("-rank")
```

For production, store the tsvector in a `GeneratedField` and index it with GIN:

```python
from django.db.models import GeneratedField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField, SearchVector

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    search_vector = GeneratedField(
        expression=SearchVector("name", "description", config="english"),
        output_field=SearchVectorField(),
        db_persist=True,
    )

    class Meta:
        indexes = [GinIndex(fields=["search_vector"], name="product_search_gin")]
```

---

## Summary

- **Constraints:** Use `CheckConstraint`, `UniqueConstraint(condition=...)`, `ExclusionConstraint` for DB-level invariants. Cross-table constraints need triggers.
- **Triggers:** Use `django-pgtrigger` to co-locate trigger definitions with models. Use `pgtrigger.ignore()` in data migrations and tests.
- **Indexes:** B-tree for equality/range; GIN for JSONB/arrays/full-text; GiST for range overlap/geometric; BRIN for monotonically ordered append-only tables.
- **Advisory locks:** Use `pg_advisory_lock` / `pg_try_advisory_lock` for distributed mutual exclusion without touching rows.
- **Window functions:** Use Django `Window` expressions. Filtering on window results requires a subquery or raw SQL CTE.
- **JSONB:** Use `JSONField` with GIN index. Update nested keys atomically with `jsonb_set` via `Func`.
- **Partitioning:** Manage via raw migrations; create partitions ahead of time with a scheduled task.
- **Safe migrations:** Use `django-pg-zero-downtime-migrations` backend + `django-syzygy` staged deploys. Add NOT NULL columns in three steps across multiple deploys.
- **PG fields:** `ArrayField` (GIN-indexed), `HStoreField`, `DateRangeField`, `SearchVectorField` — all in `django.contrib.postgres`.


---
