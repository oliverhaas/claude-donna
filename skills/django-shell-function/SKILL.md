---
name: django-shell-function
description: Self-contained functions for `manage.py shell` paste-and-run. Use when writing ad-hoc inspection, queueing, or one-off data fixes that don't justify a management command.
user-invocable: false
---

# Django Shell Functions

For one-off jobs run via `python manage.py shell` (or `uv run python manage.py shell`). Define a function, call it, done.

If the operation will be repeated, run on a schedule, or needs CLI arguments, write a management command instead (see `django-management-commands`).

## Conventions

- All imports inside the function. Paste-and-replace works without scrolling.
- No comments, no blank lines inside the function body.
- Print progress as you go: every batch, every per-row action.

## Example: queue tasks

```python
def queue_sync():
    from orders.models import Shipment
    from sync.tasks.sync_shipment import sync_shipment_task
    qs = Shipment.objects.filter(merchant__sandbox=False, synced_at__isnull=True)
    print(f"Queueing {qs.count()} shipments...")
    for s in qs.iterator(chunk_size=1000):
        print(f"shipment {s.id}: queueing")
        sync_shipment_task.delay(shipment_id=s.id)
    print("Done")
```

## Large querysets: stream with `.iterator()`

Anything more than a few hundred rows (especially with `select_related` / `prefetch_related`) goes through `.iterator(chunk_size=1000)`. It streams from the DB instead of materialising the whole set.

For mutations, buffer up to 1000 and flush with `bulk_update` / `bulk_create`:

```python
def backfill_reference_numbers():
    from orders.models import Order
    qs = Order.objects.filter(reference_number__isnull=True)
    total = qs.count()
    print(f"Backfilling {total} orders...")
    buffer = []
    for i, order in enumerate(qs.iterator(chunk_size=1000), 1):
        order.reference_number = f"ORD-{order.id:06d}"
        buffer.append(order)
        if len(buffer) == 1000:
            Order.objects.bulk_update(buffer, ["reference_number"])
            print(f"  flushed {i}/{total}")
            buffer.clear()
    if buffer:
        Order.objects.bulk_update(buffer, ["reference_number"])
    print("Done")
```

Bulk operations bypass `.save()` and signals: see `django-orm-queries` and `django-save-hooks` for when that matters.

## Confirm per step: y/n/a/q

For destructive or expensive per-row operations, print the planned action and prompt before executing. `a` switches to auto mode, `q` quits.

```python
def cleanup_drafts():
    from products.models import Product
    qs = Product.objects.filter(status="draft", merchant__active=False)
    total = qs.count()
    print(f"Found {total} drafts to delete")
    auto = False
    for i, p in enumerate(qs.iterator(chunk_size=1000), 1):
        print(f"[{i}/{total}] delete {p.id} ({p.name!r})")
        if not auto:
            choice = input("  y/n/a/q? ").strip().lower()
            if choice == "q":
                break
            if choice == "n":
                continue
            if choice == "a":
                auto = True
        p.delete()
        print("  deleted")
    print("Done")
```

## Alternative: dry-run flag

Two-call pattern. First call previews, second call executes:

```python
def expire_promotions(dry_run=True):
    from django.utils import timezone
    from promotions.models import Promotion
    qs = Promotion.objects.filter(end_date__lt=timezone.now(), status="active")
    total = qs.count()
    prefix = "[dry-run] " if dry_run else ""
    print(f"{prefix}Expiring {total} promotions")
    for p in qs.iterator(chunk_size=1000):
        print(f"  {p.id}: {p.name!r}")
        if not dry_run:
            p.status = "expired"
            p.save(update_fields=["status"])
    print("Done")
```

Run `expire_promotions()` to inspect, then `expire_promotions(dry_run=False)` to execute.
