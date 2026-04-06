---
name: django-orm-queries
description: Guidelines for writing efficient Django ORM queries. Use when writing, reviewing, or optimizing querysets, annotations, or database access patterns.
user-invocable: false
---

# Django ORM Queries

Write efficient database queries that minimize round-trips and fetch only necessary data.

## Cachalot Caching

If using `django-cachalot`, it caches queries on "static" tables (categories, attributes, countries, etc.). Focus optimization on dynamic data (orders, products, user data) and high-traffic endpoints.

## Be Careful with Bulk Operations

**WARNING:** `bulk_create()`, `bulk_update()`, and `queryset.update()` bypass `post_save` hooks and overridden `.save()` methods containing important business logic.

```python
# Default: Use .save() to preserve business logic
for product in products:
    product.price *= 1.1
    product.save()

# Use only if verified no hooks/custom save() logic
Product.objects.filter(category=old).update(category=new)
```

## Basic Optimizations

**Prevent N+1 queries, default to `prefetch_related()`:**
- `prefetch_related('fk', 'reverse_fk', 'm2m')` works for **all** relation types (separate queries)
- `select_related('fk')` is ForeignKey/OneToOne only (SQL JOIN)

**Why `prefetch_related()` is almost always preferred:**
1. **No duplicate objects**: `select_related()` creates separate Python objects per row, even when multiple rows reference the same FK target. `prefetch_related()` reuses the same object, which is memory-efficient and consistent.
2. **Cacheable**: Separate queries can hit `django-cachalot` cache (e.g., `Country` table is cached, so `prefetch_related("country")` may be a cache hit instead of a DB query).
3. **The extra roundtrip rarely matters**: One additional simple query is negligible compared to the safety and caching benefits.

**When `select_related()` is fine:**
- **Single-object queries** (`.get()`, `.first()`): when saving one roundtrip actually matters
- **Multi-object queries**: only when there is almost no duplication across rows AND the saved roundtrip matters AND the related table is not cached via cachalot

**Minimize data transfer:**
- `only('id', 'name')` to fetch specific fields
- `defer('description', 'large_field')` to exclude fields

**Efficient checks:**
- `queryset.exists()` for boolean checks
- `queryset.count()` only when you need the number
- `aggregate(Sum('total'))` and `annotate(count=Count('items'))` for DB-level calculations
- **Note:** If you need the queryset anyway, use Python: `len()`, `bool()`, `sum()` are often better than extra DB queries

**Avoid queries in loops:**
```python
orders = Order.objects.prefetch_related('items')
for order in orders:
    items = order.items.all()
```

## Less Obvious Optimizations

### Evaluated Querysets: Use Python Operations

```python
products = list(Product.objects.all())  # Evaluated
count = len(products)  # Not .count()
has_products = bool(products)  # Not .exists()
```

### Iterator (also with Prefetch)

Iterator is useful for iterating over large querysets to keep the memory usage in check by using `chunk_size`.

Contrary to older sources, `.iterator()` works with `prefetch_related()`:

```python
for order in Order.objects.prefetch_related('items').iterator(chunk_size=1000):
    for item in order.items.all():
        process_item(item)
```

### Prefetch + .all() and Python Filtering

Calling `.all()` on prefetched relations doesn't re-query, even with custom `Prefetch()`. Filter in Python if you've already prefetched all objects:

```python
orders = Order.objects.prefetch_related(
    Prefetch('items', queryset=OrderItem.objects.select_related('product'))
)

for order in orders:
    items = order.items.all()  # No query
    active = [i for i in order.items.all() if i.is_active]  # Filter in Python
```

### Fill Missing Prefetches

Use `prefetch_related_objects()` to add prefetches on already-fetched instances. Only fetches what's not already loaded:

```python
from django.db.models import prefetch_related_objects

product = Product.objects.prefetch_related('variants').get(id=1)

prefetch_related_objects(
    [product],
    'variants',                      # Already loaded - skipped
    'variants__options',             # Missing - fetched
    'attributes__attribute_group',   # Missing - fetched
)
```

### Use `values()` for Read-Only Data

For large read-only datasets (exports, API responses, analytics), prefer `values()` over `only()`. Returns dicts instead of model instances with no instantiation overhead, lower memory, and can be 10x+ faster.

```python
from django.db.models import F

products = Product.objects.values(
    'name',
    'price',
    brand_name=F('brand__name'),
    category_name=F('category__name'),
)
```

Use `only()` when you need model methods, save capability, or related object traversal.

## Avoiding Duplicates When Filtering Across Relations

Filtering across relationships (JOINs) can produce duplicate rows. Use `Exists()` with `OuterRef()` instead of `distinct()`:

```python
from django.db.models import Exists, OuterRef

# Find merchants who have at least one active product
Merchant.objects.filter(
    Exists(
        Product.objects.filter(
            merchant=OuterRef("id"),
            status="active",
        )
    )
)
```

**Why `Exists()`:** Stops at first match (fast), no duplicates, works on all databases, no ordering restrictions. `distinct()` is expensive for large fields; `distinct(*fields)` is PostgreSQL-only.

## Subqueries for Execution Order

SQL executes WHERE before ORDER BY. When you need to filter a pre-ordered/pre-distincted set, use a subquery:

```python
# Get latest edition of each book, then filter by release year
Book.objects.filter(
    id__in=Book.objects.order_by("name", "-edition").distinct("name").values("id"),
    release_year__isnull=False,
)
```

Without the subquery, `filter()` would apply before `order_by()`, returning wrong results.

## Database Functions

```python
from django.db.models import F, Value
from django.db.models.functions import Concat, Coalesce

Product.objects.filter(sale_price__lt=F('price') * 0.5)
Product.objects.annotate(full_name=Concat('brand__name', Value(' - '), 'name'))
Product.objects.annotate(display_price=Coalesce('sale_price', 'price'))
```

## Indexing

Django auto-indexes ForeignKey fields, unique constraints, and primary keys (`id`). Use APM/monitoring tools to identify slow queries, then add indexes.

**Note:** An index on `id` always exists. Often ordering by `id` is good enough - no need for a separate `created_at` index.

```python
class Product(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE)  # Auto-indexed
    sku = models.CharField(max_length=100, unique=True)  # Auto-indexed
    status = models.CharField(max_length=50, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['merchant', 'status']),  # Composite
        ]
```

## Combined Example

```python
orders = Order.objects.select_related(
    'merchant',
    'shipping_address__country'
).prefetch_related(
    Prefetch('items', queryset=OrderItem.objects.select_related('product__brand'))
).annotate(
    item_count=Count('items')
).only(
    'id', 'status', 'total', 'merchant__name'
)

for order in orders.iterator(chunk_size=1000):
    for item in order.items.all():  # No query
        print(f"{item.product.brand.name}: {item.product.name}")
    pending = [i for i in order.items.all() if i.status == 'pending']  # Filter in Python
```

## Prefetch-Aware Model Methods

`.order_by().first()`, `.filter()`, `.count()` etc. bypass the prefetch cache. Check if a relation is prefetched (e.g. via a helper or `hasattr(instance, '_prefetched_objects_cache')`) to branch between `.all()` + Python ops (prefetched) and queryset ops (not prefetched).

## Debugging Query Count

To verify query efficiency during development or review:

```python
from django.db import connection, reset_queries

reset_queries()
# ... your code ...
print(f"Queries: {len(connection.queries)}")
```

## Safe Concurrent Updates (Locking)

`UPDATE` automatically acquires row-level locks. Use atomic conditional updates instead of explicit locking:

```python
# Atomic update: lock held only during query execution (~1ms)
updated = Order.objects.filter(id=order_id, status="open").update(status="shipped")
if not updated:
    raise OrderAlreadyTransitioned()
```

**Use `select_for_update()` only** when complex Python logic is needed between read and write, since every increase of time holding a lock will introduce more problems.

**Add DB constraints as safety net:**
```python
models.CheckConstraint(check=models.Q(quantity__gte=0), name="quantity_non_negative")
```

## Summary

- **Prevent N+1:** Default to `prefetch_related()` for all relation types. It avoids duplicate objects, enables cachalot cache hits, and the extra roundtrip rarely matters
- **`select_related()` only when:** single-object queries where the roundtrip matters, or multi-object queries with near-zero duplication, no cachalot caching, and a meaningful roundtrip cost
- **Fill missing prefetches:** `prefetch_related_objects()` only fetches what's not already loaded
- **Bulk ops:** Be careful, they bypass post_save hooks or additional logic in `.save()`
- **Evaluated querysets:** Use `len()` and `bool()` instead of `.count()` and `.exists()`
- **Iterator + prefetch:** Works in our Django version
- **Prefetch + Python filter:** Filter in Python if already prefetched
- **Read-only data:** Use `values()` instead of `only()` for exports/analytics (no model overhead)
- **Cachalot:** Static tables cached; optimize dynamic data
- **Indexing:** Use APM/monitoring tools to identify slow queries
- **Avoid duplicates:** Use `Exists()` with `OuterRef()` when filtering across relations
- **Execution order:** Use `id__in=Subquery(...)` to filter after ordering/distinct
- **Safe concurrent updates:** Use atomic `.filter(...).update()` + check rows affected; reserve `select_for_update()` for complex Python logic between read and write


---
