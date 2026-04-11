---
name: django-caching
description: Cache backend selection, key design, invalidation, per-view and per-object caching, stampede prevention, and async patterns. Use when adding or reviewing caching in Django.
user-invocable: false
---

# Django Caching

## Backend Configuration

Use `django-cachex` for all Redis/Valkey caches. It provides Valkey and Redis backends with async support, extended data structures, distributed locking, pluggable serializers/compressors, and a built-in admin interface.

```python
# settings.py
CACHES = {
    "default": {
        "BACKEND": "django_cachex.cache.ValkeyCache",
        "LOCATION": env("REDIS_URL", default="valkey://localhost:6379/1"),
        "OPTIONS": {
            "compressor": "django_cachex.compressors.zlib.ZlibCompressor",
            "serializer": "django_cachex.serializers.msgpack.MessagePackSerializer",
        },
        "KEY_PREFIX": "myapp",
        "VERSION": 1,
        "TIMEOUT": 300,  # 5 minutes default; None = no expiry
    },
    "sessions": {
        "BACKEND": "django_cachex.cache.ValkeyCache",
        "LOCATION": env("REDIS_SESSIONS_URL", default="valkey://localhost:6379/2"),
        "KEY_PREFIX": "sess",
        "TIMEOUT": 86400,  # 1 day
    },
}
```

Use a **separate Redis database** (or separate Redis instance) for sessions vs. general caching. This prevents session eviction when the general cache fills up.

For Redis, use `django_cachex.cache.RedisCache` as the `BACKEND` and `redis://` URLs.

## Cache Key Design

### Namespacing pattern

```python
# cache_keys.py  (one file per app, or a shared util)
ARTICLE_DETAIL = "article:{pk}:detail"
ARTICLE_LIST   = "article:list:page:{page}"
USER_PERMS     = "user:{user_id}:perms"
SIDEBAR        = "sidebar:v1"


def article_detail_key(pk: int) -> str:
    return ARTICLE_DETAIL.format(pk=pk)


def article_list_key(page: int) -> str:
    return ARTICLE_LIST.format(page=page)


def user_perms_key(user_id: int) -> str:
    return USER_PERMS.format(user_id=user_id)
```

Rules:
- Always include the entity type and primary identifier.
- Include a version token (`v1`, `v2`) when the shape of cached data changes rather than purging all keys manually.
- Never hard-code raw strings at call sites — centralise in `cache_keys.py`.

## Per-View Caching

### `cache_page`

```python
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.vary import vary_on_headers

# Public page, same for all users, 15 minutes
@cache_page(60 * 15)
def public_landing(request):
    ...

# Vary by Accept-Language header (localised content)
@cache_page(60 * 15)
@vary_on_headers("Accept-Language")
def localised_view(request):
    ...

# Never cache authenticated dashboards
@never_cache
def dashboard(request):
    ...
```

`cache_page` stores the full rendered response. Only use it for views that:
- Are the same for all (or easily segmented) users.
- Do not depend on request-specific session or CSRF state.

### URL-level cache in `urls.py`

Prefer this over decorating class-based views — CBVs and `cache_page` interact awkwardly.

```python
from django.views.decorators.cache import cache_page

urlpatterns = [
    path("products/", cache_page(60 * 10)(ProductListView.as_view()), name="product-list"),
]
```

## Per-Object / Fragment Caching

### Basic pattern

```python
from django.core.cache import cache
from .cache_keys import article_detail_key

ARTICLE_TTL = 60 * 30  # 30 minutes

def get_article(pk: int) -> dict:
    key = article_detail_key(pk)
    data = cache.get(key)
    if data is None:
        article = Article.objects.select_related("author", "category").get(pk=pk)
        data = serialize_article(article)
        cache.set(key, data, timeout=ARTICLE_TTL)
    return data
```

### `get_or_set` shorthand

```python
def get_sidebar_items() -> list[dict]:
    return cache.get_or_set(
        "sidebar:v1",
        lambda: list(Category.objects.values("id", "name", "slug")),
        timeout=60 * 60,
    )
```

Use `get_or_set` when populating is cheap and stampede risk is low. For expensive operations, use the lock-based approach below.

## Cache Stampede Prevention

When many requests hit a cold cache simultaneously, each fetches from the DB — the "thundering herd". Prevent it with a lock.

```python
import time
from django.core.cache import cache

LOCK_TIMEOUT = 10  # seconds to hold lock
LOCK_WAIT    = 0.05  # poll interval while waiting

def get_expensive_report(report_id: int) -> dict:
    key      = f"report:{report_id}:v1"
    lock_key = f"report:{report_id}:lock"

    data = cache.get(key)
    if data is not None:
        return data

    # Try to acquire lock
    if cache.add(lock_key, "1", timeout=LOCK_TIMEOUT):
        try:
            # Re-check after acquiring lock (another worker may have populated)
            data = cache.get(key)
            if data is None:
                data = _build_report(report_id)
                cache.set(key, data, timeout=60 * 30)
        finally:
            cache.delete(lock_key)
        return data

    # Another worker holds the lock — wait and retry
    deadline = time.monotonic() + LOCK_TIMEOUT
    while time.monotonic() < deadline:
        time.sleep(LOCK_WAIT)
        data = cache.get(key)
        if data is not None:
            return data

    # Fallback: recompute without lock
    return _build_report(report_id)
```

`cache.add()` is atomic — it only sets the key if absent. This is the correct primitive for distributed locks with Redis.

## Invalidation Strategies

### 1. Time-based (TTL only)

Default approach. Set a TTL appropriate for staleness tolerance. No explicit invalidation code needed.

```python
cache.set(key, value, timeout=300)
```

### 2. Signal-based invalidation

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .cache_keys import article_detail_key

@receiver(post_save, sender=Article)
@receiver(post_delete, sender=Article)
def invalidate_article_cache(sender, instance, **kwargs):
    cache.delete(article_detail_key(instance.pk))
```

Prefer signal-based invalidation for objects that change infrequently but must be fresh immediately (user profiles, product details, permissions).

Always invalidate inside `transaction.on_commit` to avoid deleting the cache key before the DB transaction commits, which would cause the next read to re-cache stale data:

```python
from django.db import transaction

@receiver(post_save, sender=Article)
def invalidate_article_cache(sender, instance, **kwargs):
    transaction.on_commit(lambda: cache.delete(article_detail_key(instance.pk)))
```

### 3. Versioned cache keys

Increment a version counter to instantly invalidate all related keys without enumeration:

```python
def get_article_version(pk: int) -> int:
    return cache.get(f"article:{pk}:version", default=0)

def bump_article_version(pk: int) -> None:
    try:
        cache.incr(f"article:{pk}:version", delta=1)
    except ValueError:
        cache.set(f"article:{pk}:version", 1)

def article_versioned_key(pk: int) -> str:
    v = get_article_version(pk)
    return f"article:{pk}:v{v}:detail"

# Invalidation: just bump the version
@receiver(post_save, sender=Article)
def invalidate_on_save(sender, instance, **kwargs):
    transaction.on_commit(lambda: bump_article_version(instance.pk))
```

Old keys become unreachable and expire naturally via TTL. No need to explicitly delete them.

### 4. `delete_pattern` for bulk invalidation (django-cachex)

```python
from django.core.cache import cache

# Delete all keys matching a prefix (Redis SCAN + DEL, non-blocking)
cache.delete_pattern("article:*")
```

Use sparingly — it scans the keyspace. Fine for deployments, admin actions, or low-frequency bulk invalidation.

## django-cachex Usage Patterns

`django-cachex` exposes cache client methods beyond the standard Django cache API.

```python
# Pipelining (MULTI/EXEC) via the cache client
from django.core.cache import cache

with cache._cache.pipeline(transaction=True) as pipe:
    pipe.set("key1", "val1", timeout=300)
    pipe.set("key2", "val2", timeout=300)
    pipe.execute()

# Increment a counter atomically (key must exist; raises ValueError if missing)
cache.add("page:views:home", 0)  # no-op if already set
cache.incr("page:views:home", delta=1)

# Touch (reset TTL without changing value)
cache.touch("session:abc123", timeout=3600)
```

Connection error handling — on connection failures, the underlying valkey-py/redis-py raises connection errors. Catch them when caching is optional:

```python
from django.core.cache import cache
from valkey.exceptions import ConnectionError as ValkeyConnectionError

try:
    cache.set(key, data, timeout=300)
except ValkeyConnectionError:
    pass  # Degrade gracefully; DB is the source of truth
```

## cachalot — ORM Query Caching

`django-cachalot` transparently caches ORM query results and invalidates them on writes. Use it when:

- Read/write ratio on hot tables is very high (>10:1).
- Queries are repeated frequently with the same parameters.
- Query result sets are small enough to serialize cheaply.

**Do not use cachalot** for:
- Tables with very frequent writes (invalidations overwhelm the cache benefit).
- Queries that return large result sets.
- Raw SQL (`connection.execute`) — cachalot cannot intercept these.

### Configuration

```python
# settings.py
INSTALLED_APPS = [
    ...
    "cachalot",
]

CACHALOT_CACHE = "default"
CACHALOT_TIMEOUT = 60 * 5  # 5 minutes
CACHALOT_ONLY_CACHABLE_TABLES = {  # opt-in: only cache these tables
    "catalog_category",
    "catalog_tag",
    "auth_permission",
}
```

Opt-in mode (`CACHALOT_ONLY_CACHABLE_TABLES`) is safer than opt-out — explicitly decide which tables benefit.

### Selective disable

```python
from cachalot.api import cachalot_disabled

# Run a query without caching (e.g., admin reporting, fresh reads)
with cachalot_disabled():
    count = Order.objects.filter(status="pending").count()
```

### Manual invalidation

```python
from cachalot.api import invalidate_table, invalidate_all

invalidate_table(Article)   # invalidate all cached queries on this model
invalidate_all()            # nuclear option — use only in tests or migrations
```

## Async Cache Access

All cache methods have `a`-prefixed async equivalents. They wrap sync implementations via `sync_to_async` internally (not native async I/O).

```python
from django.core.cache import cache

async def get_article_async(pk: int) -> dict:
    key = article_detail_key(pk)
    data = await cache.aget(key)
    if data is None:
        article = await Article.objects.select_related("author").aget(pk=pk)
        data = serialize_article(article)
        await cache.aset(key, data, timeout=ARTICLE_TTL)
    return data

# Other async primitives
await cache.adelete(key)
await cache.aget_or_set(key, lambda: default_value(), timeout=300)
many = await cache.aget_many(["k1", "k2"])
await cache.aset_many({"k1": "v1", "k2": "v2"}, timeout=300)
await cache.aincr("counter", delta=1)
```

For async stampede prevention, use `cache.aadd()` as the lock primitive:

```python
acquired = await cache.aadd(lock_key, "1", timeout=LOCK_TIMEOUT)
```

## Common Pitfalls

**Caching mutable Python objects** — `cache.set` serializes at call time. Mutating the returned object does not update the cache. Treat cached values as immutable.

**Missing key prefix** — without `KEY_PREFIX`, keys from different apps or environments collide in shared Redis. Always set `KEY_PREFIX` in settings.

**Caching per-user data under a shared key** — data specific to a user must include the user ID in the cache key or it leaks across users.

**Long TTLs without write invalidation** — TTL is not a substitute for invalidation on write. Use signal-based invalidation for objects that must be fresh when changed.

**`cache.get_or_set` is not atomic** — two concurrent callers can both get `None`, both compute the value, and both call `set`. Acceptable for cheap operations; use the lock pattern for expensive ones.

**Forgetting `transaction.on_commit`** — invalidate cache inside `on_commit`, not directly in a signal receiver. Deleting the cache key mid-transaction causes the next read to re-cache the pre-commit DB state.

**`TIMEOUT=None` leaks memory** — keys without expiry accumulate indefinitely. Only use `None` for truly static data. Always set an explicit TTL otherwise.

**Serialization errors** — don't cache objects that can't be pickled/msgpack-serialized (file handles, locks, generator instances). Cache plain dicts, lists, primitives, and simple dataclasses.
