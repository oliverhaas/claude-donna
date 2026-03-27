---
name: general-python
description: Python coding conventions for this project. Use when writing or reviewing any Python code.
user-invocable: false
---

# Python Conventions

## Function Signatures

Use keyword-only arguments (start params with `*`):

```python
def process_order(*, order_id: int, user: User | None = None) -> Order:
    ...
```

Use `str | None` not `Optional[str]`. Always type-hint parameters and return values.

## Closure Variable Capture in Loops

Lambdas and closures inside loops capture variables by reference, not value.

```python
# Wrong -- all callbacks use the last item
for item in items:
    transaction.on_commit(lambda: process(item.id))

# Correct -- default arg captures current value
for item in items:
    transaction.on_commit(lambda i=item: process(i.id))
```

Applies to `transaction.on_commit`, `threading.Timer`, task scheduling, or any closure created in a loop.

---
