---
name: celery-tasks
description: Guidelines for implementing Celery tasks. Use when writing or reviewing async task code.
user-invocable: false
---

# Celery Tasks Guidelines

## Basic Task Implementation

**REQUIRED: Use keyword-only arguments** (mandatory `*`):

```python
from celery import shared_task

@shared_task
def my_task(*, user_id: int, action: str) -> None:
    """Process user action."""
    pass

# Usage
my_task.delay(user_id=123, action="update")
```

**Exception:** Positional arguments are only allowed when absolutely required by Celery features (e.g., chord callbacks passing results as positional args).

**Task Location:**
- App-specific tasks: `{app_name}/tasks/{task_name}.py`
- Cross-cutting tasks: `tasks/tasks/`
- Periodic tasks: `tasks/periodic_tasks.py`

**Important:** You have to import the tasks to `{app_name}/tasks/__init__.py`, otherwise the task will not be registered with Celery.

## Queue Selection

**Two queues:**
- `default` - Most tasks (short, light on resources)
- `heavy` - Long-running or resource-intensive tasks

```python
from tasks.celery.queues import CeleryQueue

@shared_task(queue=CeleryQueue.HEAVY)
def export_report(*, merchant_id: int) -> None:
    pass
```

## Calling Tasks

```python
# Async execution
my_task.delay(user_id=123)

# With countdown (seconds)
my_task.apply_async(kwargs={"user_id": 123}, countdown=60)

# After DB transaction commits (via DjangoTask)
@transaction.atomic
def create_user(request):
    user = User.objects.create(...)
    welcome_email.delay_on_commit(user_id=user.id)
```

## Advanced Features (via BaseTask)

All tasks automatically support:

**Debouncing** (collapse rapid calls):
```python
@shared_task(debounce={"delay": 60})
def update_search_index(*, product_id: int):
    pass
```

**Batching** (accumulate and execute together):
```python
@shared_task(batch={"flush_delay": 10, "flush_size": 100, "by": "item_ids"})
def process_items(*, user_id: int, item_ids: list[int]):
    pass
```

**Long delays** (> 60s use Redis instead of broker):
```python
# Automatically uses Redis for efficient storage
my_task.apply_async(kwargs={"user_id": 123}, countdown=3600)
```

## Redis Transport

Use `celery-redis-plus` as the Redis transport (see `packages` skill). It is the preferred broker/backend for all Celery deployments in this project.

## Best Practices

1. **REQUIRED:** Use keyword-only arguments (`*`) unless Celery features absolutely require positional args
2. Include full type hints
3. Make tasks idempotent (safe to retry)
4. Use `delay_on_commit()` for DB-dependent tasks
5. Pass IDs, not objects (serialization)
6. Positional arguments only when absolutely necessary (e.g., chord callbacks)


---
