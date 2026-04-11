---
name: django-debugging
description: Systematic debugging patterns for the Django stack. Use when diagnosing ORM issues, migration failures, template errors, Celery failures, signal bugs, or middleware problems.
user-invocable: false
---

# Django Debugging

Opinionated debugging playbook for the Django stack. Work through the relevant section top-to-bottom.

## Debug Tooling Setup

### django-debug-toolbar (local only)

```python
# settings/local.py
INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
INTERNAL_IPS = ["127.0.0.1"]

# urls.py
from django.conf import settings
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
```

The SQL panel shows all queries per request, their times, and duplicate detection.

### shell_plus (django-extensions)

```bash
uv run python manage.py shell_plus --print-sql   # auto-imports all models + prints SQL
uv run python manage.py shell_plus --ipython
```

### Query logging to console

```python
# settings/local.py
LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}
```

## ORM Issues

### N+1 Queries

Symptoms: hundreds of identical queries, slow list views, high query counts in debug-toolbar.

```python
# Identify in shell_plus
qs = Order.objects.all()
for o in qs:
    print(o.customer.name)  # N+1: one query per iteration

# Fix: FK/OneToOne → select_related
qs = Order.objects.select_related("customer")

# Fix: reverse FK / M2M → prefetch_related
qs = Product.objects.prefetch_related("variants")

# Fix: nested relations
from django.db.models import Prefetch
qs = Product.objects.prefetch_related(
    Prefetch("variants", queryset=Variant.objects.select_related("warehouse"))
)

# Fix: only need one field → annotate instead of loading the object
from django.db.models import F
qs = Order.objects.annotate(customer_name=F("customer__name")).values("id", "customer_name")
```

Verify with `assertNumQueries`:

```python
from django.test.utils import CaptureQueriesContext
from django.db import connection

def test_order_list_query_count(db):
    OrderFactory.create_batch(10)
    with CaptureQueriesContext(connection) as ctx:
        list(Order.objects.select_related("customer"))
    assert len(ctx.captured_queries) == 1
```

### Lazy Evaluation Surprises

QuerySets are lazy — they evaluate on iteration, slicing, or explicit calls.

- If a QS is passed to a function that calls `.count()` and then iterates, that's two DB hits. Evaluate to `list()` once when you need both.
- Filtering after slicing raises `TypeError` at query time, not at definition.
- A QS passed to a template that renders it multiple times hits the DB multiple times. Pass `list()` or use `{% with %}` to cache.

### QuerySet Caching

A QS caches its result after the first full evaluation. Partial evaluations (`exists()`, `count()`, index access) do NOT populate the cache.

```python
qs = MyModel.objects.filter(active=True)
list(qs)          # evaluates and caches
qs[0]             # uses cache — fast
qs.filter(x=1)   # new QS — no cache

# Trap: count() does NOT cache; iterating afterwards hits DB again
if qs.count() > 0:     # DB hit 1
    for obj in qs: ... # DB hit 2

# Fix: evaluate once when you need both the check and the objects
objects = list(qs)
if objects:
    for obj in objects: ...

# Use exists() only when you don't need the objects
if qs.exists():
    do_something_without_the_objects()
```

### Database-Level Debugging

```sql
-- Enable query logging in PostgreSQL (psql)
SET log_min_duration_statement = 0;  -- log all queries

-- EXPLAIN a slow query
EXPLAIN ANALYZE SELECT * FROM orders_order WHERE customer_id = 42;
```

```python
# Get raw SQL from a Django QS
qs = Order.objects.filter(customer_id=42).select_related("customer")
print(qs.query)  # prints SQL without bind params

# Run EXPLAIN ANALYZE via Django
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("EXPLAIN ANALYZE " + str(qs.query))
    for row in cursor.fetchall():
        print(row[0])
```

## Migration Failures

### Checklist

```bash
uv run python manage.py showmigrations | grep -E '\[ \]|ERROR'
uv run python manage.py makemigrations --check --dry-run  # conflicts?
uv run python manage.py migrate --plan                    # what would run?
```

### Dependency Conflicts (after branch merge)

```bash
uv run python manage.py makemigrations --merge
# If auto-merge fails: delete conflicting migration from your branch, regenerate
uv run python manage.py makemigrations app_name
```

### Migration Won't Apply (DB state mismatch)

```bash
# Inspect the SQL first
uv run python manage.py sqlmigrate app_name 0042_the_migration

# If DB already has the change (e.g., manual ALTER), fake it
uv run python manage.py migrate app_name 0042_the_migration --fake
```

Only use `--fake` when certain the schema already matches.

### Data Migration Errors

The two most common causes:

1. **Importing the real model instead of the historical model** — always use `apps.get_model()`:

```python
def forwards(apps, schema_editor):
    MyModel = apps.get_model("myapp", "MyModel")
    MyModel.objects.filter(old_field="x").update(new_field="y")
```

2. **Large datasets without batching** — data migrations run in one transaction by default; a failure rolls back everything. For large tables, set `atomic = False` and batch:

```python
class Migration(migrations.Migration):
    atomic = False

    def forwards(apps, schema_editor):
        MyModel = apps.get_model("myapp", "MyModel")
        batch = []
        for obj in MyModel.objects.iterator(chunk_size=1000):
            obj.new_field = compute(obj)
            batch.append(obj)
            if len(batch) >= 1000:
                MyModel.objects.bulk_update(batch, ["new_field"])
                batch.clear()
        if batch:
            MyModel.objects.bulk_update(batch, ["new_field"])
```

Note: `apps.get_model()` returns a historical model — signals are not fired, and `.save()` must be called explicitly (or use `bulk_update`/`bulk_create`).

### Squash Issues

After squashing, both the squashed migration and the originals coexist. Django applies the squash automatically once all original migrations are marked as applied. Common fix when the squash appears unapplied:

```bash
uv run python manage.py migrate --fake app_name 0001_squashed_0042
```

Remove the original migration files and the `replaces` attribute only after every environment (including production) has run the squash.

## Template Errors

### TemplateSyntaxError

Read the line number in the traceback. Common causes:

- Typo in tag name: `{% blocktrans %}` (removed in Django 4) vs `{% blocktranslate %}`
- Using DTL-only tags in Jinja2 or vice versa (see `django-jinjafy` skill)
- Unclosed block tag: `{% if %}` without `{% endif %}`

```bash
# Quick syntax check without loading a browser
uv run python manage.py shell -c \
  "from django.template.loader import get_template; get_template('myapp/my_template.html')"
```

### Missing Context Variable

Django templates silently render `""` for missing variables. To surface them locally:

```python
# settings/local.py
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "OPTIONS": {
        "string_if_invalid": "MISSING_VAR[%s]",
    },
}]
```

### Include Failures

`{% include %}` silently swallows errors in production (`DEBUG=False`). The error surfaces in development. Check:

- Template path is correct relative to configured `DIRS` / `APP_DIRS`
- The included template's required context variables are present in the parent context
- No circular includes

## Celery Task Failures

### Serialization Errors

Pass only PKs to tasks, not model instances — instances are not JSON serializable.

```python
my_task.delay(instance.pk)

@shared_task
def my_task(instance_pk: int) -> None:
    instance = MyModel.objects.get(pk=instance_pk)
    ...
```

Other non-serializable types: `Decimal`, naive/aware `datetime` mismatches, custom class instances. Pass only JSON-safe primitives (int, str, float, list, dict).

### Connection / Broker Issues

```bash
# Check broker connectivity
uv run python manage.py shell -c \
  "from celery import current_app; print(current_app.control.inspect().ping())"

# Check what workers are doing
uv run celery -A myproject inspect active
uv run celery -A myproject inspect reserved
```

Common misconfigurations:

```python
# Missing result backend — task.get() hangs indefinitely
CELERY_RESULT_BACKEND = "redis://localhost:6379/1"

# Task routed to a queue with no workers consuming it
CELERY_TASK_ROUTES = {"myapp.tasks.heavy": {"queue": "heavy"}}
# Must start a worker for that queue:
# celery -A myproject worker -Q heavy
```

### Task Dispatched Before DB Commit

Tasks dispatched inside `@transaction.atomic` may run before the transaction commits — the worker fetches the object and gets `DoesNotExist`. Always dispatch with `on_commit`:

```python
with transaction.atomic():
    obj = MyModel.objects.create(...)
    transaction.on_commit(lambda: my_task.delay(obj.pk))

# Or delay_on_commit if available (celery-redis-plus / custom mixin)
my_task.delay_on_commit(obj.pk)
```

### Debugging a Failing Task Locally

```python
# Run eagerly (in-process, no worker) for a full traceback
from myapp.tasks import my_task
my_task.apply(args=[42]).get(propagate=True)

# Or configure all tasks to run synchronously in tests/dev
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```

## Common Django Tracebacks

| Traceback | Root cause |
|---|---|
| `DoesNotExist: MyModel matching query does not exist` | `.get()` found no rows — use `.filter().first()` or guard with `try/except` |
| `MultipleObjectsReturned` | `.get()` found more than one row — add more constraints to the query |
| `RelatedObjectDoesNotExist` | Accessing a nullable `OneToOneField` reverse accessor when no related object exists |
| `OperationalError: no such table` | Migration not applied — run `migrate` |
| `ProgrammingError: column "x" does not exist` | Migration not applied or pointed at wrong database |
| `IntegrityError: UNIQUE constraint failed` | Duplicate insert — use `get_or_create` or handle the exception |
| `IntegrityError: NOT NULL constraint failed` | Saving without a required field — call `full_clean()` before `save()` |
| `SuspiciousOperation: Invalid HTTP_HOST header` | Hostname not in `ALLOWED_HOSTS` |
| `ImproperlyConfigured` | Settings not loaded, or circular import in `AppConfig.ready()` |
| `AppRegistryNotReady` | Importing models at module level before `django.setup()` has run |

## Signal Debugging

### Double-Firing

Signals fire once per `connect()` call. Double-firing usually means either:
- The module containing `connect()` is imported more than once
- `dispatch_uid` is missing, allowing duplicate registrations

```python
# Always use dispatch_uid to prevent duplicate connections
post_save.connect(
    my_handler,
    sender=MyModel,
    dispatch_uid="myapp.handlers.my_handler",
)

# Preferred: @receiver decorator (cleaner, dispatch_uid still required)
from django.dispatch import receiver
from django.db.models.signals import post_save

@receiver(post_save, sender=MyModel, dispatch_uid="myapp.handlers.on_mymodel_save")
def on_mymodel_save(sender, instance, created, **kwargs):
    ...
```

### Verifying Connected Receivers

```python
# In shell_plus — list all receivers for post_save on a specific sender
from django.db.models.signals import post_save
from myapp.models import MyModel

for receiver in post_save._live_receivers(MyModel):
    print(receiver)
```

### Ordering Issues

Signals give no ordering guarantees between receivers. If order matters:
- Consolidate into a single receiver that calls functions in the correct sequence
- Or chain receivers explicitly by having one call the next

### Disabling Signals in Tests

```python
from unittest.mock import patch
from django.db.models.signals import post_save

def test_without_post_save_signal(db):
    with patch.object(post_save, "send", return_value=[]):
        MyModel.objects.create(name="test")

# Disconnect/reconnect approach for a specific handler
def test_without_specific_handler(db):
    post_save.disconnect(my_handler, sender=MyModel)
    try:
        MyModel.objects.create(name="test")
    finally:
        post_save.connect(my_handler, sender=MyModel)
```

## Middleware Debugging

### Ordering Bugs

`MIDDLEWARE` is applied top-to-bottom on the request path, bottom-to-top on the response path. Dependencies must come earlier in the list.

```python
# AuthenticationMiddleware reads from the session — SessionMiddleware must come first
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
```

If `request.user` is always `AnonymousUser` when it shouldn't be: check that `SessionMiddleware` is above `AuthenticationMiddleware`.

### Async/Sync Mismatches

Any sync middleware in an ASGI stack forces the entire request through a thread pool:

```
# Django logs this at DEBUG level:
Asynchronous handler adapted for middleware 'myapp.middleware.MyMiddleware'
```

Any middleware without `async_capable = True` causes this. See `django-middleware` skill for the dual sync/async pattern.

### Tracing the Request Lifecycle

```python
# Temporary debug middleware — insert at the top of MIDDLEWARE
class DebugRequestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import logging
        log = logging.getLogger("debug.request")
        log.debug(
            "incoming: %s %s  user=%s",
            request.method,
            request.path,
            getattr(request, "user", "<not set>"),
        )
        response = self.get_response(request)
        log.debug("outgoing: %s", response.status_code)
        return response
```

