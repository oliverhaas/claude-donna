---
name: tests-infrastructure
description: Test infrastructure for pytest-django + testcontainers + xdist. Covers container setup, parallel DB/Redis, autouse fixtures, and Celery worker testing. Use when setting up or modifying the test plumbing layer.
user-invocable: false
---

# Test Infrastructure

Plumbing layer for pytest-django, testcontainers, and pytest-xdist parallel execution. See `tests-general` for test conventions and `django-tdd` for TDD workflow.

## PostgreSQL Container

Start the container at settings import time, not in a fixture. Django needs the DB connection configured before any fixture runs.

```python
# postgres_container.py
from testcontainers.postgres import PostgresContainer

_pg_container = None

def get_pg_container() -> PostgresContainer:
    global _pg_container
    if _pg_container is None:
        _pg_container = PostgresContainer(
            "postgres:16-alpine",
            username="test",
            password="test",
            dbname="test_db",
        ).with_command(
            "postgres"
            " -c fsync=off"
            " -c synchronous_commit=off"
            " -c full_page_writes=off"
            " -c max_locks_per_transaction=256"
        ).with_tmpfs({"/var/lib/postgresql/data": "rw"})
        _pg_container.start()

        # Create extensions on template1 so all test DBs inherit them
        import psycopg
        with psycopg.connect(_pg_container.get_connection_url()) as conn:
            conn.autocommit = True
            conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            # Add any other extensions or collations here
    return _pg_container

def stop_pg_container():
    global _pg_container
    if _pg_container is not None:
        _pg_container.stop()
        _pg_container = None
```

### Deterministic port assignment for xdist

Each worker gets the same port across runs via a seeded RNG. Avoids port collisions without coordination.

```python
import hashlib
import os
import random

def get_pg_port() -> int:
    uid = os.environ.get("PYTEST_XDIST_TESTRUNUID", "")
    worker = os.environ.get("PYTEST_XDIST_WORKER", "master")
    seed = hashlib.sha256(f"{uid}{worker}".encode()).digest()
    rng = random.Random(seed)
    return rng.randint(15000, 15999)
```

### Settings integration

```python
# settings/testing.py
from myproject.postgres_container import get_pg_container

pg = get_pg_container()

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": pg.dbname,
        "USER": pg.username,
        "PASSWORD": pg.password,
        "HOST": pg.get_container_host_ip(),
        "PORT": pg.get_exposed_port(5432),
    }
}
```

### Teardown

Stop the container in `pytest_unconfigure`, not in a fixture finalizer:

```python
# conftest.py (root)
def pytest_unconfigure(config):
    from myproject.postgres_container import stop_pg_container
    stop_pg_container()
```

## Valkey/Redis Container

Session-scoped autouse fixture. Port allocation uses a two-phase process for xdist safety.

### Phase 1: Master allocates ports

```python
# conftest.py (root)
import socket

def pytest_configure(config):
    worker_count = config.option.numprocesses or 1
    base_port = _find_consecutive_ports(worker_count, range_start=10000, range_end=19999)
    os.environ["PYTEST_REDIS_CONTAINER_BASE_PORT"] = str(base_port)

def _find_consecutive_ports(count: int, range_start: int, range_end: int) -> int:
    for candidate in range(range_start, range_end - count):
        if all(_port_available(candidate + i) for i in range(count)):
            return candidate
    raise RuntimeError(f"Cannot find {count} consecutive available ports")

def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False
```

### Phase 2: Worker computes its port

```python
def _worker_redis_port() -> int:
    base = int(os.environ["PYTEST_REDIS_CONTAINER_BASE_PORT"])
    worker = os.environ.get("PYTEST_XDIST_WORKER", "gw0")
    worker_num = int(worker.replace("gw", "")) if worker != "master" else 0
    return base + worker_num
```

### Redis fixture

```python
# conftest.py or fixtures/redis_container.py
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session", autouse=True)
def redis_container():
    port = _worker_redis_port()
    container = RedisContainer("valkey/valkey:8.1").with_bind_ports(6379, port)
    container.start()
    yield container
    container.stop()
```

### DB separation in settings

```python
# settings/testing.py
REDIS_PORT = _worker_redis_port()
REDIS_URL = f"valkey://localhost:{REDIS_PORT}"

CACHES = {
    "default": {
        "BACKEND": "django_cachex.cache.ValkeyCache",
        "LOCATION": f"{REDIS_URL}/0",
    },
}

CELERY_BROKER_URL = f"{REDIS_URL}/3"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/4"
```

DB 0 for cache, DB 3 for Celery broker, DB 4 for result backend. Separate DBs prevent test cache clears from wiping Celery state.

## Test Settings Detection

Auto-detect the test environment without requiring env var setup:

```python
# settings.py
import os
import sys

APP_ENV = os.getenv(
    "APP_ENV",
    "testing" if ("test" in sys.argv or "pytest" in sys.modules) else "local",
)

# Load environment-specific settings
from myproject.env_settings import *  # noqa: F403
```

This loads `env_settings/testing.py` automatically when running under pytest.

## Autouse Fixtures

### CASCADE flush

Monkey-patch PostgreSQL's `sql_flush` to use CASCADE. Prevents FK constraint errors when flushing between tests.

```python
# fixtures/sql_flush_cascade.py
import pytest

@pytest.fixture(scope="session", autouse=True)
def sql_flush_cascade():
    from django.db.backends.postgresql.operations import DatabaseOperations

    original = DatabaseOperations.sql_flush

    def cascading_flush(self, style, tables, *, reset_sequences=False, allow_cascade=False):
        return original(self, style, tables, reset_sequences=reset_sequences, allow_cascade=True)

    DatabaseOperations.sql_flush = cascading_flush
    yield
    DatabaseOperations.sql_flush = original
```

### Clear cache

```python
# fixtures/cache.py
import pytest

@pytest.fixture(autouse=True)
def clear_cache(redis_container):
    """Clear all Django caches before each test."""
    from django.core.cache import caches
    for cache in caches.all():
        cache.clear()
```

Depends on `redis_container` to ensure Valkey is available before clearing.

### N+1 query detection

Phase-aware: only active during the test body (call phase), not during fixture setup/teardown where factory creation triggers expected queries.

```python
# fixtures/nplus1.py
import pytest
from threading import local

_phase = local()

def pytest_runtest_setup(item):
    _phase.current = "setup"

def pytest_runtest_call(item):
    _phase.current = "call"

def pytest_runtest_teardown(item):
    _phase.current = "teardown"

@pytest.fixture(autouse=True)
def nplus1_guard(request):
    if request.node.get_closest_marker("nplus1_allow"):
        yield
        return

    from django_nplus1 import Profiler

    profiler = Profiler()
    profiler.start()
    yield
    profiler.stop()

    if getattr(_phase, "current", None) == "call":
        violations = profiler.get_violations()
        if violations:
            msgs = [f"  {v}" for v in violations]
            pytest.fail(f"N+1 queries detected:\n" + "\n".join(msgs))
```

Suppress for specific tests:

```python
@pytest.mark.nplus1_allow
def test_dashboard_with_known_n_plus_one(client, db):
    ...
```

Or inline:

```python
from myproject.testing import nplus1_allow

def test_complex_aggregation(db):
    with nplus1_allow(reason="Intentional per-row aggregation"):
        ...
```

## Live Server & Playwright

### Function-scoped live server

Override pytest-django's default to prevent deadlocks between transactional DB flush and in-flight browser requests.

```python
# fixtures/live_server.py
import pytest
from django.db import connections

@pytest.fixture
def live_server(request, transactional_db):
    """Function-scoped live server. Closes DB connections on teardown
    to release locks before the transactional flush."""
    from pytest_django.live_server_helper import LiveServer

    server = LiveServer("localhost")
    request.addfinalizer(server.stop)

    yield server

    connections.close_all()
```

### Playwright page cleanup

Navigate to `about:blank` on teardown to cancel in-flight HTMX/fetch requests that could hit the DB after cleanup.

```python
# fixtures/page.py
import pytest

@pytest.fixture
def page(context):
    p = context.new_page()
    yield p
    p.goto("about:blank")
    p.close()
```

## Smart xdist Scaling

Avoid xdist overhead for small test runs:

```python
# xdist.py (plugin or conftest)
import os

def pytest_xdist_auto_num_workers(config) -> int:
    cpu_count = os.cpu_count() or 1

    # Full suite: use all CPUs
    test_args = config.args
    if not test_args or test_args == ["."]:
        return cpu_count

    # Count test files specified
    test_files = [a for a in test_args if a.endswith(".py") or "::" in a]
    if len(test_files) <= 3:
        return 0  # Disable parallelism for small runs

    return min(cpu_count, len(test_files))
```

## Celery Worker Testing

Use real workers, not eager mode. `CELERY_TASK_ALWAYS_EAGER = False` in test settings.

### Fixtures

```python
# fixtures/celery.py
import gc
import pytest
from django.conf import settings

@pytest.fixture(scope="session")
def celery_config():
    return {k: v for k, v in vars(settings).items() if k.startswith("CELERY_")}

@pytest.fixture(scope="session")
def celery_worker_parameters():
    return {"queues": settings.CELERY_TASK_QUEUES}

@pytest.fixture
def celery_app(clear_cache, redis_container, cleanup_async_results, clear_kombu_event_loop):
    """Function-scoped Celery app with clean state."""
    from myproject.celery import app
    return app

@pytest.fixture
def cleanup_async_results():
    yield
    from celery.result import AsyncResult
    gc.collect()
    AsyncResult.forget_all()

@pytest.fixture
def clear_kombu_event_loop():
    """Reset kombu's global event loop to prevent cross-test pollution."""
    yield
    import kombu.utils.functional
    kombu.utils.functional._global_event_loop = None
```

### Mock fixtures for preventing dispatch

```python
@pytest.fixture
def mock_celery_task_apply_async(mocker):
    return mocker.patch("celery.app.task.Task.apply_async")

@pytest.fixture
def mock_celery_task_delay(mocker):
    return mocker.patch("celery.app.task.Task.delay")
```

Use these when you want to assert a task was dispatched without actually running it.

## pyproject.toml Config

```toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "myproject.settings"
testpaths = ["**/tests"]
addopts = "-ra -q -n auto -m 'not manual'"
markers = [
    "unit: fast, isolated unit tests",
    "e2e: end-to-end browser/integration tests",
    "manual: run only when explicitly selected",
    "nplus1_allow: suppress N+1 detection for this test",
]

[tool.coverage.run]
parallel = true
plugins = ["django_coverage_plugin"]
core = "ctrace"
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/management/commands/*",
    "manage.py",
]
```

`parallel = true` is required for xdist -- each worker writes its own `.coverage.<hash>` file. Combine with `coverage combine` after the run.

## Key Dependencies

| Package | Purpose |
|---------|---------|
| pytest-django | Django integration |
| pytest-xdist[psutil] | Parallel execution |
| pytest-cov | Coverage |
| pytest-flakefinder | Flaky test detection |
| pytest-playwright | E2E browser tests |
| pytest-split | Test splitting for CI |
| celery[pytest] | Celery worker fixtures |
| testcontainers[postgres,redis] | PostgreSQL & Valkey containers |
| factory-boy | Test data factories |
| django-nplus1 | N+1 query detection |

## Architecture Summary

- **PostgreSQL starts at import time**, not in a fixture -- ensures it's ready before Django touches the DB connection
- **Redis ports pre-allocated in master**, distributed to workers via env var -- avoids race conditions
- **PostgreSQL ports deterministic per worker** via seeded RNG -- same worker always gets same port
- **CASCADE flush** -- handles complex FK graphs without manual teardown ordering
- **Phase-aware N+1 detection** -- catches real issues while ignoring fixture noise
- **Smart worker scaling** -- avoids xdist overhead for small test runs
- **Function-scoped live server** -- prevents deadlocks between browser requests and DB flush
