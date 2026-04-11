---
name: django-middleware
description: Django middleware structure, async patterns, ordering, and testing. Use when writing custom middleware, debugging request/response lifecycle issues, or reviewing middleware stack ordering.
user-invocable: false
---

# Django Middleware

## Modern Structure

Middleware is a callable that wraps the view layer. The current pattern is a class with `__init__` and `__call__`:

```python
from collections.abc import Callable
from django.http import HttpRequest, HttpResponse


class TimingMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        # One-time setup runs here at server start.

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Code here runs before the view.
        response = self.get_response(request)
        # Code here runs after the view.
        return response
```

Never use `MiddlewareMixin` for new middleware — it exists only for legacy Django 1.x compatibility (see `django-modern-patterns` skill).

## Function-Based Middleware

Fine for simple cases:

```python
def timing_middleware(get_response):
    def middleware(request: HttpRequest) -> HttpResponse:
        response = get_response(request)
        return response
    return middleware
```

## Async Middleware

### Dual Sync/Async (Recommended for Most Cases)

Works correctly under both WSGI and ASGI without thread hops:

```python
import time
from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.http import HttpRequest, HttpResponse


class TimingMiddleware:
    async_capable = True
    sync_capable = True

    def __init__(self, get_response) -> None:
        self.get_response = get_response
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if iscoroutinefunction(self):
            return self.__acall__(request)
        t0 = time.perf_counter()
        response = self.get_response(request)
        response["X-Duration"] = f"{time.perf_counter() - t0:.3f}"
        return response

    async def __acall__(self, request: HttpRequest) -> HttpResponse:
        t0 = time.perf_counter()
        response = await self.get_response(request)
        response["X-Duration"] = f"{time.perf_counter() - t0:.3f}"
        return response
```

`markcoroutinefunction(self)` in `__init__` tells Django this instance is async-capable. `__call__` dispatches based on whether the instance was marked async at init time.

### Function-Based Dual Middleware

Use `@sync_and_async_middleware` when the logic is simple enough not to need a class:

```python
import time
from asgiref.sync import iscoroutinefunction
from django.utils.decorators import sync_and_async_middleware


@sync_and_async_middleware
def timing_middleware(get_response):
    if iscoroutinefunction(get_response):
        async def middleware(request: HttpRequest) -> HttpResponse:
            t0 = time.perf_counter()
            response = await get_response(request)
            response["X-Duration"] = f"{time.perf_counter() - t0:.3f}"
            return response
    else:
        def middleware(request: HttpRequest) -> HttpResponse:
            t0 = time.perf_counter()
            response = get_response(request)
            response["X-Duration"] = f"{time.perf_counter() - t0:.3f}"
            return response
    return middleware
```

### Async-Only Middleware

When the middleware itself requires async (e.g., it awaits I/O directly), mark it async-only so Django raises an error if it is placed in a WSGI stack:

```python
from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.http import HttpRequest, HttpResponse


class AsyncOnlyMiddleware:
    async_capable = True
    sync_capable = False

    def __init__(self, get_response) -> None:
        if not iscoroutinefunction(get_response):
            raise ValueError("AsyncOnlyMiddleware requires an async handler")
        self.get_response = get_response
        markcoroutinefunction(self)

    async def __call__(self, request: HttpRequest) -> HttpResponse:
        # Await external I/O here without sync_to_async overhead.
        response = await self.get_response(request)
        return response
```

See `django-asyncio` skill for ORM async methods, auth, and session async variants.

## Performance Warning: Sync Middleware in ASGI

Any synchronous middleware in `MIDDLEWARE` causes Django to wrap the **entire** request/response cycle in a thread pool thread. Check for:

```
Asynchronous handler adapted for middleware 'myapp.middleware.MyMiddleware'
```

in debug logs. Every such adaptation is a thread hop that negates async throughput benefits.

## Process Hooks

The old `process_request` / `process_response` / `process_exception` / `process_view` hooks from `MiddlewareMixin` translate to explicit positions in `__call__`:

```python
class HookEquivalentsMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # process_request equivalent: runs before routing + view.
        if not request.user.is_authenticated:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden()

        response = self.get_response(request)

        # process_response equivalent: runs after view, always.
        response["X-Frame-Options"] = "DENY"
        return response

    def process_view(self, request: HttpRequest, view_func, view_args, view_kwargs):
        # Called just before Django calls the view, after URL routing.
        # Return None to continue, or a response to short-circuit.
        return None

    def process_exception(self, request: HttpRequest, exception: Exception):
        # Called when the view raises an unhandled exception.
        # Return a response to handle it, or None to propagate.
        import logging
        logging.getLogger(__name__).exception("Unhandled error", exc_info=exception)
        return None
```

`process_view` and `process_exception` are still valid hooks in the modern class-based style — they do not require `MiddlewareMixin`.

## Middleware Ordering

`MIDDLEWARE` is an ordered list. Each layer wraps the next. The first entry is the outermost wrapper.

**Standard Django ordering (innermost last):**

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",       # 1st: HTTPS, HSTS, headers
    "django.contrib.sessions.middleware.SessionMiddleware", # 2nd: session before auth
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # needs session above it
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

**Key ordering rules:**

- `SessionMiddleware` must come before `AuthenticationMiddleware` (auth reads from session).
- `SecurityMiddleware` goes first — it handles redirects and security headers before anything else.
- `CsrfViewMiddleware` before your views; `CsrfViewMiddleware` reads cookies set by session.
- Your custom middleware: place after `AuthenticationMiddleware` if it needs `request.user`; place before `SecurityMiddleware` only for very early short-circuits (unusual).
- Whitenoise (static files) goes right after `SecurityMiddleware` so static files bypass auth.

## Per-Request State

### Preferred: Request Attributes

The cleanest approach — attach data directly to the request object:

```python
class CurrentTenantMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Attach tenant to the request; views access it via request.tenant.
        request.tenant = self._resolve_tenant(request)
        return self.get_response(request)

    def _resolve_tenant(self, request: HttpRequest):
        from tenants.models import Tenant
        host = request.get_host().split(":")[0]
        return Tenant.objects.filter(domain=host).first()
```

### contextvars for Non-Request Code

When downstream code (signals, service layer, Celery tasks spawned inline) needs the value but cannot accept it as a parameter, use `contextvars.ContextVar`:

```python
import contextvars
from django.http import HttpRequest, HttpResponse

_current_user: contextvars.ContextVar = contextvars.ContextVar("current_user", default=None)


class CurrentUserMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        token = _current_user.set(getattr(request, "user", None))
        try:
            return self.get_response(request)
        finally:
            _current_user.reset(token)


def get_current_user():
    return _current_user.get()
```

`ContextVar` is safe under both threads (WSGI) and coroutines (ASGI). Each request gets its own context copy.

### Avoid threading.local

`threading.local` breaks under ASGI (multiple coroutines share a thread) and leaks state across requests when thread pools reuse threads. Replace with `contextvars.ContextVar`.

## Short-Circuiting Requests

Return a response from `__call__` before calling `get_response` to skip the view entirely:

```python
from django.http import HttpResponse


class MaintenanceModeMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        from django.conf import settings
        if getattr(settings, "MAINTENANCE_MODE", False):
            if not request.path.startswith("/admin/"):
                return HttpResponse("Down for maintenance.", status=503)
        return self.get_response(request)
```

## Testing Middleware

Test middleware in isolation using `RequestFactory`, not `Client`, to avoid the full middleware stack:

```python
import pytest
from django.test import RequestFactory

from myapp.middleware import CurrentTenantMiddleware


@pytest.fixture
def rf():
    return RequestFactory()


def make_get_response(status=200, content=b"ok"):
    def get_response(request):
        from django.http import HttpResponse
        return HttpResponse(content, status=status)
    return get_response


def test_tenant_attached_to_request(rf, db):
    from tenants.factories import TenantFactory
    tenant = TenantFactory(domain="acme.example.com")

    request = rf.get("/", HTTP_HOST="acme.example.com")
    middleware = CurrentTenantMiddleware(make_get_response())
    middleware(request)

    assert request.tenant == tenant


def test_maintenance_mode_returns_503(rf, settings):
    settings.MAINTENANCE_MODE = True
    request = rf.get("/some/path/")
    middleware = MaintenanceModeMiddleware(make_get_response())
    response = middleware(request)

    assert response.status_code == 503


def test_maintenance_mode_passes_admin(rf, settings):
    settings.MAINTENANCE_MODE = True
    request = rf.get("/admin/")
    middleware = MaintenanceModeMiddleware(make_get_response())
    response = middleware(request)

    assert response.status_code == 200
```

For async middleware use `AsyncRequestFactory` (Django 4.1+) and `pytest-asyncio`:

```python
import pytest
from django.test import AsyncRequestFactory

from myapp.middleware import TimingMiddleware


@pytest.fixture
def arf():
    return AsyncRequestFactory()


@pytest.mark.asyncio
async def test_async_timing_header(arf):
    async def get_response(request):
        from django.http import HttpResponse
        return HttpResponse("ok")

    request = arf.get("/")
    middleware = TimingMiddleware(get_response)
    response = await middleware(request)

    assert "X-Duration" in response
```

## Common Patterns

### Adding Security Headers

```python
class SecurityHeadersMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "geolocation=(), microphone=()"
        return response
```

### Logging Request Timing

```python
import logging
import time

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, get_response) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        t0 = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 1),
            },
        )
        return response
```

See `logging` skill for structured logging conventions.

## Summary

- Use class-based middleware with `__init__` + `__call__`. No `MiddlewareMixin`.
- For dual sync/async: set `async_capable`/`sync_capable`, call `markcoroutinefunction(self)` in `__init__`, dispatch via `__acall__`.
- For per-request state: attach to `request` (preferred) or use `contextvars.ContextVar` (not `threading.local`).
- `process_view` and `process_exception` work as class methods without `MiddlewareMixin`.
- Middleware ordering matters: session before auth, security first.
- Any sync middleware in an ASGI stack forces a thread hop for the whole request.
- Test with `RequestFactory` / `AsyncRequestFactory` in isolation, not `Client`.
