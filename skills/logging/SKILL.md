---
name: logging
description: Logging guidelines and best practices. Use when adding or reviewing logging code.
user-invocable: false
---

# Logging Guidelines

## Setup

Use the standard library `logging` module:

```python
import logging

logger = logging.getLogger(__name__)
```

For Django projects, use Better Stack (betterstack.com) for log aggregation and monitoring.

## Formatting

Use `%` formatting in log calls, not f-strings. This enables lazy evaluation (the string is only formatted if the log level is active):

```python
# Good
logger.info("Order %s processed for user %s", order_id, user_id)

# Bad: always evaluates the f-string
logger.info(f"Order {order_id} processed for user {user_id}")
```

## Structured Data via `extra=`

Pass structured context as `extra=` rather than concatenating it into the message. The log aggregator (Better Stack, Datadog, etc.) indexes those keys as filterable fields:

```python
logger.info(
    "Batch import completed: %d products processed", count,
    extra={"merchant_id": merchant.id, "duration_ms": duration_ms},
)
```

Keys in `extra=` must not collide with `LogRecord` attributes (`message`, `args`, `levelname`, etc.) — pick distinct names like `order_id` rather than `id`.

## Request/Task-Wide Context

For values that should appear on every log line in a request or background task (user id, request id, merchant id), set them once at the boundary instead of threading them through every call. Two common implementations:

- **A `contextvars.ContextVar` helper + a logging `Filter`** that copies the current value onto each `LogRecord`. Bind in a middleware (request) or task `before_start` signal (Celery), reset on teardown.
- **A `LoggingContextMiddleware` / custom Celery `Task` base class** that exposes a `set_context(**kwargs)` helper writing into the same `ContextVar`.

```python
# Pseudocode for a project-level helper
set_context(merchant_id=merchant.id, order_id=order.id)
logger.info("Processing order")  # automatically tagged with merchant_id, order_id
```

This avoids `extra=` repetition and guarantees per-record-attribution stays consistent across calls.

## Log Levels

**CRITICAL**: System-critical failures requiring immediate attention. Triggers alerts.

**ERROR**: Needs attention. Failed operations, data integrity issues.
- Not for user input errors or expected validation failures.

**WARNING**: Unexpected but handled. Deprecated usage, missing config, retryable failures.

**INFO**: Important business events. Completed operations, major milestones.
- Not for routine per-item processing.

**DEBUG**: Development details. Variable values, control flow. Disabled in production.

```python
logger.critical("Database connection pool exhausted")
logger.error("Failed to sync order %s after 3 retries", order_id)
logger.warning("Product %s has no price for country %s", product_id, country_code)
logger.info("Batch import completed: %d products processed", count)
logger.debug("Product variant lookup returned %s", variant)
```

## Exception Logging

Use `logger.exception()` inside except blocks to capture the traceback:

```python
try:
    process_order(order_id)
except Exception:
    logger.exception("Error processing order %s", order_id)
    raise
```

---
