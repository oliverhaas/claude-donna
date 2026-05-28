---
name: tests-celery
description: Guidelines for testing Celery tasks. Use when writing tests for async tasks.
user-invocable: false
paths:
  - "**/tests/**/*.py"
---
# Testing Celery Tasks

## Default: Mock .delay() + Test Logic Separately

```python
def test_order_processing_triggers_task(mock_base_task_delay):
    process_order_workflow(order_id=order.id)
    mock_base_task_delay.assert_called()

def test_process_order_task_logic():
    result = process_order.apply(kwargs={"order_id": order.id}).get()
    assert result == "expected_output"
```

Use `.apply()` (eager execution through the task pipeline), not `.run()`. `.apply()` goes through the full task machinery (serialization, signals, custom base-task setup) which mirrors production behavior and is required for tools that hook into those signals (e.g. nplusone detection via `task_prerun`).

**Available fixtures** (from root `conftest.py`): `mock_base_task_delay`, `mock_base_task_apply_async`

## Real Celery Worker

To test actual Celery behavior (retry logic, custom task classes, etc.), use `celery_worker`:

```python
def test_full_flow_queue_to_execution(celery_worker):
    result = some_task.delay(arg=value)
    result.get(timeout=10)
    assert result.successful()
```

The worker uses testcontainers Redis/Valkey for broker and backend.

## Testing Custom Task Features

For custom task classes (BatchedTask, DebouncedTask, DelayedTask), test internal methods directly:

```python
def test_batch_add_items():
    """Test batching logic without queuing."""
    kwargs = {"item_ids": [1, 2, 3], "resource_id": "res-1"}
    total_size = batched_task._batch_add_items(batch_key, kwargs)
    assert total_size == 3
```

## Caveats

**Never set `CELERY_TASK_ALWAYS_EAGER`.** Settings-isolation issues, hides race conditions, and makes eager execution implicit (so a test that "happens to work" can silently rely on it). Make eager execution explicit per test by calling `.apply()`.

## Summary

- **Mock `.delay()`** to test task triggering
- **Call `.apply()`** to test business logic (not `.run()`)
- **Use `celery_worker`** only for testing Celery-specific behavior


---
