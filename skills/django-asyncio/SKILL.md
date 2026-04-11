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

### ORM Async Pitfalls

**Lazy evaluation in async code.** QuerySets are lazy — they don't evaluate until iterated or a terminal method is called. Simply building a queryset in async code is fine, but accessing it as if it were already evaluated is not:

```python
# Wrong: triggers sync evaluation
qs = Product.objects.filter(active=True)
first = qs[0]  # SynchronousOnlyOperation

# Correct
first = await Product.objects.filter(active=True).afirst()
```

**`select_related` vs `prefetch_related` in async.** `select_related` uses a SQL JOIN and is resolved in the same query — the async variant fetches everything at once. `prefetch_related` issues separate queries and works when awaited properly via `aprefetch_related_objects`, but accessing a prefetch cache on an instance without first awaiting the prefetch raises `SynchronousOnlyOperation`:

```python
# Wrong: accessing prefetch cache synchronously
obj = await Order.objects.aget(pk=pk)
items = list(obj.items.all())  # SynchronousOnlyOperation

# Correct: use aprefetch_related_objects after fetching the instance
from django.db.models import aprefetch_related_objects

obj = await Order.objects.aget(pk=pk)
await aprefetch_related_objects([obj], "items")
items = [i async for i in obj.items.all()]
```

**Accessing related objects via attribute in async.** Accessing a `ForeignKey` or `OneToOneField` attribute on an instance without `select_related` hits the database synchronously:

```python
# Wrong
order = await Order.objects.aget(pk=pk)
name = order.customer.name  # SynchronousOnlyOperation

# Correct: select_related in the query
order = await Order.objects.select_related("customer").aget(pk=pk)
name = order.customer.name  # safe, already loaded
```

**`sync_to_async` wrapping for sync ORM helpers.** When a sync function that uses the ORM is called from async context, wrap it with `sync_to_async`:

```python
from asgiref.sync import sync_to_async

def get_active_products():
    return list(Product.objects.filter(active=True))

async def my_view(request):
    products = await sync_to_async(get_active_products)()
```

`sync_to_async` runs the function in a thread pool executor by default, so it is safe for blocking I/O. For thread-unsafe code (e.g. code that relies on thread-local state), pass `thread_sensitive=True` (the default) to run it in the main thread's executor.

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

### Middleware Async/Sync Bridge Issues

**Sync middleware forces thread wrapping.** Any sync middleware in `MIDDLEWARE` causes Django to wrap the entire request/response cycle in a thread via `AsyncToSync`, negating the performance benefit of async views. Symptoms show up as `"Asynchronous handler adapted for middleware ..."` in debug logs.

**Mixing middleware modes breaks the chain.** If you write an async middleware but call `get_response` without `await`, the response is a coroutine object, not an `HttpResponse`. Always await it in async branches:

```python
# Wrong
async def middleware(request):
    response = get_response(request)  # coroutine, not response
    return response

# Correct
async def middleware(request):
    response = await get_response(request)
    return response
```

**Custom `process_request` / `process_response` hooks are sync.** Middleware classes using the old-style `process_request`/`process_response` interface are always sync. Convert them to `__call__`-style before adding to an async-first stack.

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

### Auth and Session Pitfalls in Async Views

**`request.user` vs `request.auser()`.** In async views, `request.user` is technically available but accessing it can trigger a sync database lookup if the user hasn't been loaded yet. Always use `await request.auser()` in async views:

```python
# Risky: may work but relies on lazy loading already being done
user = request.user

# Correct
user = await request.auser()
```

**Session access without `await`.** `request.session` dict-style access (`request.session["key"]`) reads from an in-memory dict that was populated synchronously by `SessionMiddleware`. This is safe for reading, but `asave()` must be awaited. However, to be safe and explicit, prefer the async session methods.

**`@login_required` with async views.** The redirect logic runs synchronously. `request.user` must already be populated by `AuthenticationMiddleware`; the decorator does not async-check the session.

### Cache Pitfalls in Async Context

**Third-party cache backends may not implement async methods.** Only the built-in cache backends (`LocMemCache`, `DatabaseCache`, `FileBasedCache`, `RedisCache` via `django-redis`) implement the `a`-prefixed methods. Custom or third-party backends that don't override them fall back to `sync_to_async` wrapping automatically, which is safe but creates a thread per call.

**`cache.get_or_set` race condition is the same in async.** `aget_or_set` is not atomic. Under concurrent requests, the default factory can be called multiple times. Use a distributed lock if the factory is expensive.

## Signals

Async dispatch with `asend()` and `asend_robust()`. Receivers are auto-adapted: sync receivers called via `asend()` get wrapped with `sync_to_async`, async receivers called via `send()` get wrapped with `async_to_sync`. Async receivers in `asend()` run concurrently via `asyncio.gather()`.

**Receiver grouping (Django 6.0).** To reduce sync/async context switches, Django 6.0 groups receivers by type before dispatching — all sync receivers run together, then all async receivers (or vice versa). Async receivers execute concurrently within their group via `asyncio.gather()`. This means an async receiver registered *before* a sync receiver may still execute *after* it. Do not rely on registration order for signal receivers used with `asend()`.

```python
from django.dispatch import Signal

order_placed = Signal()

async def notify_warehouse(sender, **kwargs):
    await send_notification(kwargs["order_id"])

order_placed.connect(notify_warehouse)

# In async code
await order_placed.asend(sender=OrderService, order_id=order.id)
```

### Signal Pitfalls in Async Context

**Built-in Django signals (`post_save`, `pre_delete`, etc.) use `send()`, not `asend()`.** They are always dispatched synchronously. An async receiver connected to `post_save` will be wrapped in `async_to_sync` and block the calling thread. Keep ORM signal receivers sync, or dispatch your own signal with `asend()` from async code.

**Exceptions in concurrent receivers.** `asend()` uses `asyncio.gather()` for the async receiver group, which by default raises on the first exception (potentially cancelling others in the group). Use `asend_robust()` instead to get a list of `(receiver, result_or_exception)` pairs without cancellation:

```python
results = await order_placed.asend_robust(sender=OrderService, order_id=order.id)
for receiver, result in results:
    if isinstance(result, Exception):
        logger.error("Signal receiver %s failed: %s", receiver, result)
```

**`sync_to_async` wrapping sync signal receivers has overhead.** Each sync receiver connected to an `asend()` dispatch gets its own thread. For high-throughput signals with many sync receivers, the thread overhead adds up. Prefer async receivers or use `send()` and keep receivers fast.

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

## Django Tasks Framework (Django 6.0)

Django 6.0 ships a built-in Tasks framework for running code outside the request-response cycle. For straightforward background work (emails, data processing, webhooks) it replaces many Celery use cases without requiring an external task queue package.

**Define a task with `@task`:**

```python
from django.tasks import task

@task
def send_welcome_email(user_id: int) -> None:
    user = User.objects.get(pk=user_id)
    send_mail("Welcome", "Hello!", None, [user.email])
```

**Enqueue from sync or async code:**

```python
# sync context
result = send_welcome_email.enqueue(user_id=user.pk)

# async context
result = await send_welcome_email.aenqueue(user_id=user.pk)
```

**Enqueue safely after a transaction commits:**

```python
from functools import partial
from django.db import transaction

with transaction.atomic():
    user = User.objects.create(...)
    transaction.on_commit(partial(send_welcome_email.enqueue, user_id=user.pk))
```

**Configuration** via `TASKS` setting. Two built-in backends for dev/testing:

```python
# ImmediateBackend — runs tasks inline (default)
TASKS = {"default": {"BACKEND": "django.tasks.backends.immediate.ImmediateBackend"}}

# DummyBackend — records tasks without running them (useful in tests)
TASKS = {"default": {"BACKEND": "django.tasks.backends.dummy.DummyBackend"}}
```

Production setups require a third-party backend with actual worker processes (see [Django Packages task backends](https://djangopackages.org/grids/g/task-framework/)).

**Constraints:**
- Task arguments and return values must be JSON-serializable. Pass PKs, not model instances.
- Django enqueues tasks; it does not run workers. External infrastructure is still required in production.

**When to prefer Django Tasks over Celery:**
- Straightforward fire-and-forget jobs with no complex retry logic, chaining, or ETA scheduling.
- Projects that want fewer external dependencies.

**When to keep Celery:**
- Complex retry policies, chord/chain primitives, canvas workflows, beat scheduler, or existing Celery infrastructure. See the `celery-tasks` skill.

## Async Streaming

```python
from django.http import StreamingHttpResponse

async def stream_export(request: HttpRequest) -> StreamingHttpResponse:
    async def generate():
        async for product in Product.objects.values_list("name", flat=True):
            yield f"{product}\n"

    return StreamingHttpResponse(generate(), content_type="text/plain")
```

### File Uploads in Async Views

Django's file upload machinery (`request.FILES`, `InMemoryUploadedFile`, `TemporaryUploadedFile`) is synchronous. The request body has already been parsed by the time the view runs, so reading `request.FILES` is safe from async views. Writing the uploaded file to storage can be blocking:

```python
from asgiref.sync import sync_to_async

async def upload_view(request: HttpRequest) -> JsonResponse:
    f = request.FILES["file"]
    # Writing to default storage is synchronous; wrap it
    path = await sync_to_async(default_storage.save)(f.name, f)
    return JsonResponse({"path": path})
```

For large file uploads with custom async storage backends (e.g. direct-to-S3 via `aioboto3`), implement `async def _save()` in your storage class and call it directly rather than through `sync_to_async`.

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

Async transaction support is not available in Django 6.0. The underlying database drivers are synchronous; true async transaction support remains a long-term goal (DEP 0009) with no release timeline.

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

## Testing Async Django Code

### Async Test Client

Use `AsyncClient` for async views or when you want to test the full ASGI stack:

```python
from django.test import AsyncClient, TestCase

class ProductListTests(TestCase):
    async def test_product_list(self):
        client = AsyncClient()
        response = await client.get("/products/")
        assert response.status_code == 200
```

`AsyncClient` is a drop-in replacement for `Client` with `await` on every request method (`get`, `post`, `put`, `patch`, `delete`, `head`, `options`).

### pytest-asyncio

Mark async tests with `@pytest.mark.asyncio` and use `django_db` with `transaction=True` for async ORM access:

```python
import pytest

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_create_order():
    order = await Order.objects.acreate(total=100)
    assert order.pk is not None
```

`transaction=True` is required because async ORM methods run in a separate thread and need a real transaction, not the default test transaction rollback.

Configure `asyncio_mode` in `pytest.ini` / `pyproject.toml` to avoid marking every test individually:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Testing Signals with `asend`

Use `AsyncMock` when asserting that an async signal receiver was called:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_order_signal():
    handler = AsyncMock()
    order_placed.connect(handler)
    try:
        await order_placed.asend(sender=None, order_id=42)
        handler.assert_awaited_once()
    finally:
        order_placed.disconnect(handler)
```

### Testing Streaming Responses

Consume the async generator from `StreamingHttpResponse.streaming_content`:

```python
@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_stream_export():
    client = AsyncClient()
    response = await client.get("/export/")
    assert response.status_code == 200
    chunks = []
    async for chunk in response.streaming_content:
        chunks.append(chunk)
    assert len(chunks) > 0
```

## Third-Party Package Compatibility

Most Django packages are sync-only and safe to use from async views via `sync_to_async`. Some specific gaps to know:

**django-rest-framework (DRF).** DRF views are sync. Wrapping a DRF `APIView` in `sync_to_async` works but loses async benefits. For async APIs, use `django-ninja` or `djangorestframework-simplejwt` with plain async Django views.

**django-allauth / social-auth.** Authentication flows are sync. Call them via `sync_to_async` or keep authentication views sync.

**Celery.** `task.delay()` and `task.apply_async()` are sync (they push to the broker). They are safe to call from async views without wrapping — the call is fast. For result waiting, use `task.apply_async()` then `await asyncio.get_event_loop().run_in_executor(None, result.get)`. See the `celery-tasks` skill.

**django-channels.** Channels has its own async consumer model. Do not mix Channels consumers with standard async views in the same request path.

**django-storages.** The default backends are sync. For true async storage I/O, use a backend built on `aioboto3` or similar.

## Async Celery Patterns

Django 6.0 ships a built-in Tasks framework (see **Django Tasks Framework** section above) that covers simple background work without requiring Celery. Use Celery when you need complex retry logic, chaining/chord primitives, the beat scheduler, or existing Celery infrastructure.

See the `celery-tasks` skill for full Celery guidelines. Async/Celery interaction points:

**Dispatching tasks from async views.** `task.delay()` is synchronous but fast (network call to broker). It is safe to call from async code without `sync_to_async` for simple cases. If the broker call becomes a bottleneck, wrap it:

```python
from asgiref.sync import sync_to_async

await sync_to_async(notify_user.delay)(user_id=user.pk)
```

**Tasks calling async code.** Celery tasks run in a sync worker context. To call an async function from a task, use `asyncio.run()` or `async_to_sync`:

```python
from asgiref.sync import async_to_sync

@shared_task
def send_notification(*, user_id: int) -> None:
    async_to_sync(async_notify)(user_id=user_id)
```

Do not create a new event loop manually (`asyncio.new_event_loop()`) inside tasks. Use `async_to_sync` or `asyncio.run()`, which handle loop creation and cleanup correctly.

**Never await task results in an async view.** Blocking on `result.get()` from an async view defeats the purpose of async and risks deadlocking the event loop thread pool. Hand off the work to Celery and return immediately.

## asyncio Patterns Relevant to Django

**Concurrent external calls.** Use `asyncio.gather()` to fan out to multiple external services:

```python
import asyncio
import httpx

async def dashboard_view(request: HttpRequest) -> JsonResponse:
    async with httpx.AsyncClient() as client:
        orders, inventory = await asyncio.gather(
            client.get("https://orders.internal/summary"),
            client.get("https://inventory.internal/summary"),
        )
    return JsonResponse({"orders": orders.json(), "inventory": inventory.json()})
```

**Timeouts.** Always apply timeouts to external calls to avoid hanging the event loop:

```python
async with asyncio.timeout(5.0):
    result = await external_api_call()
```

**Don't block the event loop.** Any synchronous blocking call (file I/O, `time.sleep`, CPU-heavy work) inside an async view blocks the entire event loop. Offload to a thread with `sync_to_async` or `asyncio.get_event_loop().run_in_executor()`:

```python
import asyncio

async def render_view(request: HttpRequest) -> HttpResponse:
    loop = asyncio.get_event_loop()
    # CPU-bound: run in process pool
    result = await loop.run_in_executor(None, expensive_cpu_computation)
    return HttpResponse(result)
```

**`asyncio.create_task` in views.** Fire-and-forget tasks created with `asyncio.create_task()` are tied to the request's event loop run. If the response returns before the task finishes, the task may be cancelled. For reliable background work, use Django's Tasks framework (`task.aenqueue()`) or Celery.

## ASGI Deployment

Recommended servers: **granian**, **uvicorn**, **daphne**, **hypercorn**.

```bash
# granian (preferred in this project)
granian myproject.asgi:application --interface asgi

# uvicorn
uvicorn myproject.asgi:application
```

The `startproject` command creates `asgi.py` automatically. Point the ASGI server at `myproject.asgi:application`.
