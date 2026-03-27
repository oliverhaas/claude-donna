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

Use `%` formatting in log calls, not f-strings. This enables lazy evaluation -- the string is only formatted if the log level is active:

```python
# Good
logger.info("Order %s processed for user %s", order_id, user_id)

# Bad -- always evaluates the f-string
logger.info(f"Order {order_id} processed for user {user_id}")
```

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
