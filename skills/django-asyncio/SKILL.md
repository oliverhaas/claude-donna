---
name: django-asyncio
description: Async Django patterns for views, ORM, middleware, auth, cache, signals, and pagination. Use when writing or reviewing async Django code.
user-invocable: false
---

# Async Django (6.0)

## Async Views

Just declare the view as `async def`. All standard view decorators (`@login_required`, `@permission_required`, `@csrf_exempt`, `@require_GET`, etc.) work with both sync and async views.

```python
from django.http import HttpRequest, JsonResponse

async def product_list(request: HttpRequest) -> JsonResponse:
    products = [p async for p in Product.objects.values("id", "name")]
    return JsonResponse({"products": products})
```

Disconnect handling under ASGI:

```python
import asyncio

async def long_running_view(request: HttpRequest) -> HttpResponse:
    try:
        result = await expensive_operation()
        return HttpResponse(result)
    except asyncio.CancelledError:
        # Client disconnected before response
        raise
```

## Async ORM

QuerySet methods that build queries (`filter()`, `exclude()`, `order_by()`, `select_related()`, `prefetch_related()`, `values()`, `annotate()`, `all()`, etc.) don't hit the database and are safe to call from async code as-is.

Methods that **execute SQL** have `a`-prefixed async variants:

| Async | Sync | Notes |
|---|---|---|
| `await qs.aget()` | `qs.get()` | |
| `await qs.afirst()` | `qs.first()` | |
| `await qs.alast()` | `qs.last()` | |
| `await qs.acount()` | `qs.count()` | |
| `await qs.aexists()` | `qs.exists()` | |
| `await qs.acreate()` | `qs.create()` | |
| `await qs.aget_or_create()` | `qs.get_or_create()` | |
| `await qs.aupdate_or_create()` | `qs.update_or_create()` | |
| `await qs.aupdate()` | `qs.update()` | |
| `await qs.adelete()` | `qs.delete()` | |
| `await qs.abulk_create()` | `qs.bulk_create()` | |
| `await qs.abulk_update()` | `qs.bulk_update()` | |
| `await qs.aaggregate()` | `qs.aggregate()` | |
| `await qs.ain_bulk()` | `qs.in_bulk()` | |
| `await qs.alatest()` | `qs.latest()` | |
| `await qs.aearliest()` | `qs.earliest()` | |
| `await qs.acontains(obj)` | `qs.contains()` | |
| `await qs.aiterator()` | `qs.iterator()` | Use with `async for` |
| `async for obj in qs` | `for obj in qs` | Iterates results |

Model instances:

```python
await obj.asave()
await obj.adelete()
await obj.arefresh_from_db()
```

Related managers:

```python
await obj.tags.aadd(tag1, tag2)
await obj.tags.aremove(tag1)
await obj.tags.aclear()
await obj.tags.aset([tag1, tag2])
await obj.tags.acreate(name="new")
```

Prefetch helper:

```python
from django.db.models import prefetch_related_objects
await aprefetch_related_objects([obj], "tags", "category")
```

## Async Middleware

Dual sync/async middleware that works regardless of the view type:

```python
from asgiref.sync import iscoroutinefunction
from django.utils.decorators import sync_and_async_middleware

@sync_and_async_middleware
def timing_middleware(get_response):
    if iscoroutinefunction(get_response):
        async def middleware(request):
            t0 = time.perf_counter()
            response = await get_response(request)
            response["X-Duration"] = f"{time.perf_counter() - t0:.3f}"
            return response
    else:
        def middleware(request):
            t0 = time.perf_counter()
            response = get_response(request)
            response["X-Duration"] = f"{time.perf_counter() - t0:.3f}"
            return response
    return middleware
```

Async-only middleware (class-based):

```python
from asgiref.sync import iscoroutinefunction, markcoroutinefunction

class AsyncOnlyMiddleware:
    async_capable = True
    sync_capable = False

    def __init__(self, get_response):
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    async def __call__(self, request):
        response = await self.get_response(request)
        return response
```

## Auth, Sessions, Cache

The pattern is consistent: prefix with `a`. All async auth, session, and cache methods are available.

**Auth:**

```python
from django.contrib.auth import aauthenticate, alogin, alogout

user = await aauthenticate(request, username=username, password=password)
await alogin(request, user)
await alogout(request)

# From request (via AuthenticationMiddleware)
user = await request.auser()

# User model
ok = await user.ahas_perm("app.change_thing")
perms = await user.aget_all_permissions()
```

**Sessions:**

```python
value = await request.session.aget("key", default=None)
await request.session.aset("key", value)
await request.session.apop("key")
await request.session.aflush()
await request.session.acycle_key()
```

**Cache:**

```python
from django.core.cache import cache

value = await cache.aget("key")
await cache.aset("key", value, timeout=300)
await cache.adelete("key")
await cache.aget_or_set("key", default, timeout=300)
many = await cache.aget_many(["k1", "k2"])
await cache.aset_many({"k1": "v1", "k2": "v2"})
```

Note: cache async methods currently use `sync_to_async` internally, not async-native I/O.

## Signals

Async dispatch with `asend()` and `asend_robust()`. Receivers are auto-adapted: sync receivers called via `asend()` get wrapped with `sync_to_async`, async receivers called via `send()` get wrapped with `async_to_sync`. Async receivers in `asend()` run concurrently via `asyncio.gather()`.

```python
from django.dispatch import Signal

order_placed = Signal()

async def notify_warehouse(sender, **kwargs):
    await send_notification(kwargs["order_id"])

order_placed.connect(notify_warehouse)

# In async code
await order_placed.asend(sender=OrderService, order_id=order.id)
```

## AsyncPaginator (Django 6.0)

```python
from django.core.paginator import AsyncPaginator

async def product_list(request: HttpRequest) -> HttpResponse:
    paginator = AsyncPaginator(Product.objects.all(), per_page=25)
    page = await paginator.aget_page(request.GET.get("page"))

    count = await paginator.acount()
    num_pages = await paginator.anum_pages()

    has_next = await page.ahas_next()
    has_prev = await page.ahas_previous()
    objects = await page.aget_object_list()
```

## Async Streaming

```python
from django.http import StreamingHttpResponse

async def stream_export(request: HttpRequest) -> StreamingHttpResponse:
    async def generate():
        async for product in Product.objects.values_list("name", flat=True):
            yield f"{product}\n"

    return StreamingHttpResponse(generate(), content_type="text/plain")
```

## Gotchas

### Transactions are not async

`transaction.atomic()` raises `SynchronousOnlyOperation` from async code. Wrap transactional work in a sync function:

```python
from asgiref.sync import sync_to_async
from django.db import transaction

def _create_order(data: dict) -> Order:
    with transaction.atomic():
        order = Order.objects.create(**data)
        OrderLine.objects.bulk_create(data["lines"])
        return order

async def create_order_view(request: HttpRequest) -> JsonResponse:
    order = await sync_to_async(_create_order)(request.POST)
    return JsonResponse({"id": order.pk})
```

Async transaction support is under active development (DEP 0009).

### Deferred fields break in async

Fields excluded via `.only()` or `.defer()` will raise `SynchronousOnlyOperation` on access in async code. Always select all needed fields upfront.

### Sync middleware kills async performance

If any synchronous middleware is in `MIDDLEWARE`, Django wraps the entire request in a thread, negating async benefits. Check for `"Asynchronous handler adapted for middleware ..."` in debug logs.

### Connection pooling

Disable `CONN_MAX_AGE` for async. Use database-level pooling (pgbouncer) or backend connection pools instead.

### ORM async is still sync_to_async under the hood

All `a`-prefixed ORM methods delegate to sync implementations via `sync_to_async`. They don't use async database drivers. The benefit is ergonomic (no manual wrapping), not true async I/O. True async database access is planned in DEP 0009.

### No `list(queryset)` in async

Use `async for` or async comprehension instead:

```python
# Wrong: raises SynchronousOnlyOperation
products = list(Product.objects.all())

# Correct
products = [p async for p in Product.objects.all()]
```

### `DJANGO_ALLOW_ASYNC_UNSAFE`

Setting this env var disables `SynchronousOnlyOperation` checks. Useful for Jupyter/IPython shells. Never use in production.

## ASGI Deployment

Recommended servers: **granian**, **uvicorn**, **daphne**, **hypercorn**.

```bash
# granian (preferred in this project)
granian myproject.asgi:application --interface asgi

# uvicorn
uvicorn myproject.asgi:application
```

The `startproject` command creates `asgi.py` automatically. Point the ASGI server at `myproject.asgi:application`.
