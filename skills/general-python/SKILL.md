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
# Wrong: all callbacks use the last item
for item in items:
    transaction.on_commit(lambda: process(item.id))

# Correct: default arg captures current value
for item in items:
    transaction.on_commit(lambda i=item: process(i.id))
```

Applies to `transaction.on_commit`, `threading.Timer`, task scheduling, or any closure created in a loop.

## Bracketless `except` (Python 3.14+)

PEP 758 reintroduced the comma syntax for catching multiple exception types without `as`:

```python
except AttributeError, TypeError:
    ...
```

This is **valid Python 3.14+** and equivalent to `except (AttributeError, TypeError):`. It is NOT the Python 2 syntax (which meant `except AttributeError as TypeError`). Both forms are acceptable; prefer parenthesised when using `as`.

## Module Naming

Avoid dumping-ground module names like `utils.py`, `helpers.py`, `common.py`, `misc.py`, `tools.py`. They grow into unbounded grab-bags. Name modules by what lives inside them: `formatting.py`, `url_builders.py`, `retry.py`. See https://tonsky.me/blog/utils/.

## Abbreviation Casing

In `CamelCase`, capitalise the whole abbreviation: `HTTPAddress`, `URLParser`, `JSONDecoder` (not `HttpAddress`). In `snake_case`, keep it lowercase: `http_address`, `url_parser`, `json_decoder`.

## `isinstance`, not `type()`

```python
# Wrong: breaks on subclasses
if type(x) == Foo:
    ...

# Correct
if isinstance(x, Foo):
    ...
```

Compare types only when you specifically need to reject subclasses — rare.

## `open()` Requires a Context Manager

```python
# Wrong: file may leak on exception
f = open(path)
data = f.read()
f.close()

# Correct
with open(path) as f:
    data = f.read()
```

Same rule for any resource with `__enter__` / `__exit__`.

## `x not in y`, not `not x in y`

```python
if key not in mapping:
    ...
```

Python has a dedicated operator — use it.

## Use `dict.get`, Not Membership-Then-Index

```python
# Wrong: two lookups
if key in mapping:
    value = mapping[key]
else:
    value = default

# Correct
value = mapping.get(key, default)
```

## `NotImplementedError`, Not `NotImplemented`

`NotImplemented` is a singleton returned by rich-comparison methods; raising it throws `TypeError`. For "subclasses must override," raise the exception:

```python
def charge(self) -> None:
    raise NotImplementedError
```

## Named Constants Over Magic Values

Extract meaningful values to module-level constants (or `math`/`enum`):

```python
# Wrong
radius * 3.14

# Correct
import math
radius * math.pi
```

Small ubiquitous values (`0`, `1`, `-1`, index `2`) are fine inline. Extract anything with business meaning or unclear origin.

## Immutable Module-Level Constants

Module-level containers are importable and mutable — a caller can mutate shared state. Freeze them:

```python
from types import MappingProxyType

ALLOWED_STATUSES = frozenset({"draft", "published", "archived"})
DEFAULT_HEADERS = MappingProxyType({"Accept": "application/json"})
```

Use `frozenset` for sets, `tuple` for sequences, `MappingProxyType` for dicts.

---
