---
name: fix-nplus1
description: Find and fix N+1 query problems in Django views, services, or tasks.
user-invocable: true
---

# Fix N+1 Queries

Find and fix N+1 query problems in Django code. For broader query guidance, see `django-orm-queries`.

## 0. Where?

Which view, service, endpoint, or task has the N+1 problem?

Clues if you don't have a specific spot:
- `django-nplus1` raising `NPlusOneError` in tests
- High query counts in logs or APM (Datadog, Sentry, debug-toolbar)
- A slow page or API endpoint

Fix at the **entry point** (view, task, management command). Services and helpers can fill in missing prefetches with `prefetch_related_objects()` (one bulk query, not N+1), but they shouldn't lazy-load in loops.

## 1. Identify common N+1 sources

Loops are obvious; these are the easy-to-miss ones:

- `__str__` accessing FK fields (any list rendering hits it)
- Admin `list_display` callables and `list_select_related` not covering the path
- DRF/Pydantic serializers traversing relations
- Template loops: `{% for item in obj.items.all %}`
- Signal handlers fanning out queries per instance
- **Prefetch-bypassing queryset methods on a prefetched relation:** `.first()`, `.filter()`, `.exclude()`, `.order_by()`, `.count()`, `.exists()` re-query even after `prefetch_related()`. See §2 "Don't bypass the prefetch cache."

## 2. Fix

### Default to `prefetch_related()`

Works for FK, reverse FK, and M2M. Reuses related objects (no duplicates), and separate queries can hit `django-cachalot` cache for static tables.

```python
# Before: N+1
products = Product.objects.all()
for product in products:
    print(product.variants.all())

# After: two queries total
products = Product.objects.prefetch_related("variants")
```

`select_related()` is fine when:
- Single-object queries (`.get()`, `.first()`) where one roundtrip matters
- Multi-object queries with near-zero duplication AND no cachalot caching AND the saved roundtrip actually matters

### Filtered prefetches: use `Prefetch(..., to_attr=...)`

Without `to_attr`, calling `.all()`/`.filter()` on the relation re-queries because the prefetch is filtered:

```python
from django.db.models import Prefetch

orders = Order.objects.prefetch_related(
    Prefetch(
        "items",
        queryset=OrderItem.objects.filter(status="pending"),
        to_attr="pending_items",
    ),
)

for order in orders:
    order.pending_items   # list, no query
    order.items.all()     # NEW query (manager, not prefetched without to_attr)
```

### Nested relations: chain or `Prefetch(queryset=...)`

Default to `prefetch_related` at every level. With cachalot, the inner relation is often a cache hit; a JOIN can't benefit from that.

```python
# Simple chain
Product.objects.prefetch_related("variants__warehouse")

# Custom inner queryset (e.g. filtering or ordering)
Product.objects.prefetch_related(
    Prefetch(
        "variants",
        queryset=Variant.objects.prefetch_related("warehouse"),
    ),
)
```

### Don't bypass the prefetch cache

Once a relation is prefetched, only `.all()` reads from the cache. Anything else re-queries:

```python
orders = Order.objects.prefetch_related("items")

for order in orders:
    order.items.all()                                    # cache hit
    [i for i in order.items.all() if i.is_active]        # cache hit, filter in Python
    order.items.filter(is_active=True)                   # NEW query
    order.items.first()                                  # NEW query
    order.items.count()                                  # NEW query (use len(order.items.all()))
```

In helpers that may be called with or without prefetched data, branch on `hasattr(instance, "_prefetched_objects_cache")` (or a project helper like `is_prefetched`) instead of always falling back to a queryset method.

### Existence checks: `Exists()` + `OuterRef()`

A Python loop that calls `obj.children.exists()` is N+1. Push it into the parent query:

```python
from django.db.models import Exists, OuterRef

merchants = Merchant.objects.annotate(
    has_active_product=Exists(
        Product.objects.filter(merchant=OuterRef("id"), status="active"),
    ),
)
```

### Need only a field from a relation: `F()` / `values()` / `annotate()`

```python
from django.db.models import F

Order.objects.annotate(customer_name=F("customer__name")).values("id", "customer_name")
```

### Already-fetched instances: `prefetch_related_objects()`

Use this in services or helpers that need additional relations beyond what the caller prefetched. It skips relations already loaded, so it's a single bulk query per missing relation, not N+1. `django-nplus1` still attributes any remaining N+1 to the entry point, so this doesn't mask the source.

```python
from django.db.models import prefetch_related_objects

prefetch_related_objects(
    orders,
    "items",                  # already loaded, skipped
    "items__product__brand",  # missing, fetched in one query
)
```

### Large querysets: `.iterator(chunk_size=...)` + `prefetch_related()`

`.iterator()` works with `prefetch_related()` on modern Django and keeps memory bounded:

```python
for order in Order.objects.prefetch_related("items").iterator(chunk_size=1000):
    for item in order.items.all():
        process(item)
```

## 3. Verify

### `django-nplus1` via middleware and celery integration

The clean setup: enable `django-nplus1`'s **middleware** for HTTP requests and its **celery integration** for tasks in test settings, configured to raise. This catches N+1 only when it happens inside a real request or task lifecycle, which is exactly the scope you care about.

Why this beats an autouse fixture:
- Test setup queries (factories, fixture data) happen outside the entry-point lifecycle, so they don't trigger false positives. No `nplus1_allow` markers needed.
- Helper-in-isolation unit tests don't hit middleware or celery, so they don't need suppression either.
- Integration tests that go through the test client (or call a celery task) get N+1 detection automatically.

In practice this means **you rarely if ever need `nplus1_allow` or autouse guards.** Just run the test:

```bash
uv run pytest path/to/test.py -v
```

If the project uses a whitelist of known violations: **remove entries as you fix them, never add new ones.**

### Ad-hoc query counting

```python
from django.test import TestCase

class OrderViewTests(TestCase):
    def test_query_count(self):
        with self.assertNumQueries(3):
            self.client.get("/orders/")
```

Or in a shell/script:

```python
from django.db import connection, reset_queries

reset_queries()
# ... code ...
print(len(connection.queries))
```

## 4. Commit

```bash
git checkout -b fix/nplus1-describe-the-fix
git add -A && git commit -m "fix: resolve N+1 queries in describe_location"
git push --set-upstream origin fix/nplus1-describe-the-fix
gh pr create --title "fix: resolve N+1 queries in describe_location" --body ""
```
