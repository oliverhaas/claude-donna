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

@pytest.mark.unit
def test_cache_key_with_version():
    ...

@pytest.mark.e2e
def test_cache_invalidation_on_save(live_server):
    ...
```

Register markers in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: fast, isolated unit tests",
    "e2e: end-to-end browser/integration tests",
]
```

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

---
