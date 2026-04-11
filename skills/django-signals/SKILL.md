---
name: django-signals
description: Django signal patterns for decoupled side effects. Use when wiring up cross-app reactions, custom signal definitions, or async dispatch (Django 5.0+).
user-invocable: false
---

# Django Signals

Signals are for **decoupled, cross-app side effects** — when the sender shouldn't know about the receiver. They're not a general-purpose hook mechanism. If the logic belongs to the same app or model, prefer save hooks or services.

## Signals vs. Save Hooks vs. Services

| Scenario | Pattern |
|---|---|
| Post-save logic that needs dirty-field tracking or bulk support | Save hook (see `django-save-hooks` skill) |
| Business logic coordinating multiple models or external systems | Service (see `django-services` skill) |
| Cross-app reaction where the sender should not import the receiver | Signal |
| Plugin-style extensibility (third-party apps hooking in) | Signal |

Signals add indirection that makes code harder to trace. Only reach for them when the decoupling is genuinely valuable.

## Built-in Signals

```python
from django.db.models.signals import (
    pre_save,    # before Model.save()
    post_save,   # after Model.save()
    pre_delete,  # before Model.delete()
    post_delete, # after Model.delete()
    m2m_changed, # ManyToManyField add/remove/clear/set
)
from django.db.models.signals import pre_migrate, post_migrate
from django.core.signals import request_started, request_finished, got_request_exception
from django.test.signals import setting_changed
```

`post_save` passes `created: bool` and `update_fields`. `m2m_changed` passes `action` (`"pre_add"`, `"post_add"`, `"pre_remove"`, `"post_remove"`, `"pre_clear"`, `"post_clear"`) and `pk_set`.

## Receiver Registration

### Decorator (preferred)

```python
# myapp/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from orders.models import Order


@receiver(post_save, sender=Order)
def order_post_save(sender, instance: Order, created: bool, **kwargs) -> None:
    if created:
        notify_fulfillment.delay(order_id=instance.id)
```

Connect in `AppConfig.ready()` — never at module level or in `models.py`:

```python
# myapp/apps.py
class MyAppConfig(AppConfig):
    name = "myapp"

    def ready(self) -> None:
        import myapp.signals  # noqa: F401 — side effects only
```

```python
# myapp/__init__.py
default_app_config = "myapp.apps.MyAppConfig"
```

### `.connect()` (for conditional or programmatic wiring)

```python
post_save.connect(order_post_save, sender=Order, weak=False)
```

Pass `weak=False` when the receiver is a lambda or a bound method — Python's default weak reference will let it be garbage-collected otherwise.

## Custom Signals

```python
# orders/signals.py
from django.dispatch import Signal

# Name signals as verb phrases describing the event
order_placed = Signal()       # provides: order
order_cancelled = Signal()    # provides: order, reason
payment_failed = Signal()     # provides: order, error_code
```

Dispatch with keyword arguments only. Document what `kwargs` receivers can expect — there's no schema enforcement.

```python
# orders/services.py
from orders.signals import order_placed

class OrderService:
    @staticmethod
    @transaction.atomic
    def order_create(*, ...) -> Order:
        order = Order(...)
        order.full_clean()
        order.save(pre_save=False, post_save=False)
        order_placed.send(sender=OrderService, order=order)
        return order
```

Prefer `send_robust()` when you can't let a failing receiver abort the operation:

```python
results = order_placed.send_robust(sender=OrderService, order=order)
for receiver, response in results:
    if isinstance(response, Exception):
        logger.exception("Signal receiver %s failed", receiver, exc_info=response)
```

`send()` propagates the first exception. `send_robust()` catches all exceptions and returns them in the results list.

## Signal Ordering

Receivers fire in the order they connect. There is no priority system. If ordering matters, either:

1. Use a single receiver that explicitly sequences calls, or
2. Refactor to a service that calls the handlers directly

Relying on implicit receiver ordering is fragile.

## Async Signals (Django 5.0+)

Use `asend()` in async contexts. Sync receivers are automatically wrapped with `sync_to_async`; async receivers run concurrently via `asyncio.gather()`.

```python
from django.dispatch import Signal

order_placed = Signal()

async def notify_warehouse(sender, order, **kwargs) -> None:
    await warehouse_api.post_order(order.id)

order_placed.connect(notify_warehouse, weak=False)

# Dispatch from async code
await order_placed.asend(sender=OrderService, order=order)
```

Use `asend_robust()` to suppress receiver exceptions in async code, same as the sync equivalent.

Mixing sync and async receivers on the same signal is fine. Django handles the adaptation automatically.

## Transaction Timing

`post_save` fires **inside** the current transaction. If you dispatch a Celery task from a `post_save` receiver, the task may run before the transaction commits and find no row.

Use `transaction.on_commit()`:

```python
from django.db import transaction

@receiver(post_save, sender=Order)
def order_post_save(sender, instance: Order, created: bool, **kwargs) -> None:
    if created:
        transaction.on_commit(lambda: notify_fulfillment.delay(order_id=instance.id))
```

Or use `delay_on_commit()` if your task class supports it (see `celery-tasks` skill):

```python
@receiver(post_save, sender=Order)
def order_post_save(sender, instance: Order, created: bool, **kwargs) -> None:
    if created:
        notify_fulfillment.delay_on_commit(order_id=instance.id)
```

## Common Pitfalls

### Double-firing

`bulk_create()` and `bulk_update()` do **not** call `.save()`, so `pre_save`/`post_save` signals are **not** sent. If you need signals for bulk operations, send them manually or use the save-hook service pattern (see `django-save-hooks`).

`update()` on a QuerySet also skips signals.

### Circular imports

Receivers import models; models import signals; signals import receivers. Break the cycle:

- Keep signal definitions in `signals.py`, receivers in the same file or a separate `receivers.py`
- Import models inside the receiver function body if needed, not at module level
- Import `signals.py` only in `AppConfig.ready()`, never at module top level

```python
# Bad: circular import risk
# myapp/models.py
from myapp.signals import order_placed  # signals.py imports models.py

# Good: late import inside ready()
class MyAppConfig(AppConfig):
    def ready(self) -> None:
        import myapp.signals  # noqa: F401
```

### Weak references drop receivers

```python
def make_handler():
    def handler(sender, **kwargs):
        ...
    post_save.connect(handler, sender=Order)  # garbage-collected immediately
    # handler goes out of scope here

# Fix: pass weak=False, or use module-level functions
post_save.connect(handler, sender=Order, weak=False)
```

### Mutations inside receivers

Receivers should not call `.save()` on the instance they received — it re-fires the signal. Use `update_fields` to limit re-entry, or update via `QuerySet.update()`:

```python
@receiver(post_save, sender=Order)
def set_slug(sender, instance: Order, created: bool, **kwargs) -> None:
    if created and not instance.slug:
        # Wrong: Order.save() -> post_save -> set_slug -> Order.save() -> ...
        # instance.slug = slugify(instance.name)
        # instance.save()

        # Correct: bypass .save() signal re-entry
        Order.objects.filter(pk=instance.pk).update(slug=slugify(instance.name))
```

## Testing Signals

Use `mock.patch` or Django's `disconnect()` to isolate signal behavior.

### Assert a signal was sent

```python
from unittest.mock import MagicMock
from django.test import TestCase
from orders.signals import order_placed


def test_order_create_sends_signal(order_factory):
    handler = MagicMock()
    order_placed.connect(handler, weak=False)
    try:
        order = OrderService.order_create(...)
        handler.assert_called_once()
        _, kwargs = handler.call_args
        assert kwargs["order"] == order
    finally:
        order_placed.disconnect(handler)
```

### Test receiver logic directly

Prefer testing the receiver function directly rather than firing signals through the ORM:

```python
from orders.signals import order_post_save


def test_order_post_save_queues_fulfillment(order, mock_task):
    order_post_save(sender=Order, instance=order, created=True)
    mock_task.delay_on_commit.assert_called_once_with(order_id=order.id)
```

### Disconnect in tests to prevent side effects

```python
import pytest
from django.db.models.signals import post_save
from orders.signals import order_post_save


@pytest.fixture(autouse=True)
def disable_order_signals():
    post_save.disconnect(order_post_save, sender=Order)
    yield
    post_save.connect(order_post_save, sender=Order)
```

Or use `django.test.utils.isolate_apps` / `mock.patch.object(signal, "send")` for broader suppression.

## Anti-Patterns to Avoid

- Using signals for logic within the same app — use save hooks or services instead
- Importing signal receivers at module level (causes circular imports)
- Relying on receiver firing order for correctness
- Calling `.save()` on the received instance from a `post_save` receiver
- Dispatching Celery tasks directly from signals without `on_commit`
- Forgetting `weak=False` for lambda or bound-method receivers
- Using `send()` when receiver failures should be tolerated — use `send_robust()`

---
