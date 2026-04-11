---
name: fix-nplusone
description: Find and fix N+1 query problems in Django views, services, or tasks.
user-invocable: true
---

# Fix N+1 Queries

Find and fix N+1 query problems in Django code.

## 0. Where?

Which view, service, endpoint, or task has the N+1 problem?

If you have a specific file/function, start there. Otherwise, look for clues:
- `django-nplus1` or `nplusone` test output flagging the query
- Slow page loads or high query counts in logs
- A specific URL or API endpoint

## 1. Identify

Find the queryset that triggers lazy loading:

```bash
# Search for bare .all(), .filter(), .get() without select/prefetch
uv run grep -rn '\.objects\.' path/to/app/views.py
```

Common patterns that cause N+1:
- Accessing `obj.related_field` in a loop without `select_related()`
- Accessing `obj.related_set.all()` in a loop without `prefetch_related()`
- Template loops like `{% for item in obj.items.all %}`
- Serializers/Pydantic schemas that traverse relations
- `__str__` methods that access FK fields

## 2. Fix

### FK / OneToOne (single object) - use `select_related()`

```python
# Before: N+1
orders = Order.objects.all()
for order in orders:
    print(order.customer.name)  # hits DB each time

# After: single JOIN
orders = Order.objects.select_related("customer").all()
```

### Reverse FK / M2M (multiple objects) - use `prefetch_related()`

```python
# Before: N+1
products = Product.objects.all()
for product in products:
    print(product.variants.all())  # hits DB each time

# After: two queries total
products = Product.objects.prefetch_related("variants").all()
```

### Nested relations - chain or use Prefetch()

```python
from django.db.models import Prefetch

Product.objects.prefetch_related(
    Prefetch(
        "variants",
        queryset=Variant.objects.select_related("warehouse"),
    )
)
```

### When you don't need the full object - use values/annotations

```python
# Instead of loading related objects just for one field
Order.objects.annotate(
    customer_name=F("customer__name")
).values("id", "customer_name")
```

## 3. Verify

```bash
# Run the relevant tests with query counting or nplusone
uv run pytest path/to/test.py -v

# If using django-nplus1, it will fail on any remaining N+1
# Otherwise, check query count manually with assertNumQueries or django-debug-toolbar
```

## 4. Commit

```bash
git checkout -b fix/nplusone-describe-the-fix
git add -A && git commit -m "fix: resolve N+1 queries in describe_location"
git push --set-upstream origin fix/nplusone-describe-the-fix
gh pr create --title "fix: resolve N+1 queries in describe_location" --body ""
```
