---
name: tests-general
description: Testing conventions, fixtures, and unit test guidelines. Use when writing, reviewing, or fixing any tests.
user-invocable: false
---

# Testing Guidelines

## Framework and Structure

- pytest as test runner with Django's test framework.
- Only function-based tests. No `class Test...` patterns.
- Prefer unit/integration tests over end-to-end where possible.

## File Organization

One `test_<feature>.py` per feature, containing all test levels (unit, integration, e2e) for that feature. This makes it easy to run everything related to a feature you're working on:

```bash
uv run pytest tests/test_caching.py        # all tests for caching
uv run pytest tests/test_caching.py -m unit # just unit tests for caching
```

Use pytest markers to distinguish test levels:

```python
import pytest

@pytest.mark.unit
def test_cache_key_generation():
    ...

@pytest.mark.e2e
def test_cache_invalidation_on_save(live_server):
    ...

@pytest.mark.screenshot
def test_widget_default_state(widget_page, assert_screenshot):
    ...

@pytest.mark.benchmark
def test_bulk_import_performance(db, benchmark):
    benchmark(Item.objects.bulk_create, items)
```

Register markers in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: fast, isolated unit tests",
    "e2e: end-to-end browser/integration tests",
    "screenshot: visual regression tests with Playwright snapshots",
    "benchmark: pytest-codspeed performance benchmarks, run with --codspeed",
]
```

Screenshot and benchmark tests are excluded from default CI runs (`-m "not screenshot and not benchmark"`); see `tests-screenshot` and `tests-benchmarks` skills. Benchmarks use pytest-codspeed in local mode — apply `@pytest.mark.benchmark` explicitly (the fixture does not auto-mark) and run with `pytest -m benchmark --codspeed`.

## Test Functions

Name clearly: `test_[what]_[expected_outcome]`.

Follow Arrange-Act-Assert:

```python
def test_merchant_str_returns_name():
    merchant = MerchantFactory.create()
    result = str(merchant)
    assert result == "Test Merchant"
```

Test one thing per function. Keep unit tests fast and independent of external services.

## Factories Over Mocks

Use factories and real data. Only mock external APIs, hard-to-configure services, or error simulation.

```python
user = UserFactory.create()
users = UserFactory.create_batch(10)
```

Always use `Factory.create()` (not bare `Factory()`) for proper type hints. Only override defaults when relevant to the specific test. Let factories handle relationships.

## Mocking

Use `mocker` fixture (pytest-mock) to isolate external dependencies:

```python
def test_order_creation_triggers_post_save(mocker):
    mock_post_save = mocker.patch("orders.models.order._post_save_order")
    with transaction.atomic():
        order = OrderFactory.create()
    mock_post_save.assert_called_once_with(order)
```

## Fixtures

```
project/
  conftest.py              # Global fixtures
  app_name/tests/
    conftest.py            # App-specific fixtures
    test_*.py
```

```python
@pytest.fixture
def merchant():
    return MerchantFactory.create()

@pytest.fixture
def authenticated_client(client, merchant):
    user = UserFactory.create(merchant=merchant)
    client.force_login(user)
    return client
```

Scopes: `function` (default, most cases), `session` (infrastructure only).

Built-in pytest-django fixtures: `client`, `rf`, `admin_client`, `db`, `settings`, `mailoutbox`.

Share across apps by importing in conftest:
```python
from other_app.tests.conftest import some_fixture  # noqa: F401
```

## Flake Detection

After writing new tests, verify stability:

```bash
uv run pytest --flake-finder --flake-runs=20 path/to/test_file.py
```

## Anti-Patterns

### No `test_regression_*.py` files

Regression tests live in the existing module that owns the subject under test, not in a dedicated `test_regression_widget.py` or `test_bugfixes.py`. The bug context belongs in the test name and a one-line comment; the test itself belongs with the rest of the tests for that feature.

```python
# Wrong: tests/test_regression_caching.py
def test_regression_issue_142():
    ...

# Right: tests/test_caching.py (alongside the rest of the caching tests)
def test_cache_invalidation_handles_concurrent_writes():
    # Regression: GH-142. Two writes raced and clobbered the cache.
    ...
```

### No `django.test.TestCase` in pytest-django projects

If the project uses pytest-django (which all donna projects do), write function-based tests with fixtures. Never reach for `django.test.TestCase` or any class-based test pattern.

```python
# Wrong
from django.test import TestCase

class WidgetTests(TestCase):
    def test_render(self):
        ...

# Right
def test_widget_render(db):
    ...
```

See `tests-infrastructure` for fixture wiring.

### Threshold values must make semantic sense

When fixturing a threshold-based detector or assertion, the threshold has to make the test meaningful. `threshold=1` on an N+1 detector fires on every single query, so the test passes trivially and proves nothing.

```python
# Wrong: threshold=1 fires on the first query, so any test setup triggers
detector = NPlusOneDetector(threshold=1)

# Right: realistic threshold that the bug actually crosses
detector = NPlusOneDetector(threshold=10)
```

### Generic model names in feature-exploration tests

Tests that exist to explore a feature (not to test a specific user-facing model) should use neutral names like `Parent`/`Child`, `Tag`/`Item`, `A`/`B`. Don't copy domain names from a feature spec, since that ties the test to the example and obscures what's being exercised.

```python
# Wrong (in a generic prefetch test)
class Order(models.Model): ...
class Customer(models.Model): ...

# Right
class Parent(models.Model): ...
class Child(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
```
