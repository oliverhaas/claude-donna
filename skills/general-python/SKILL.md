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

## Early Returns and Guard Clauses

Validate inputs at the top and return early. Nested `if`/`else` pyramids are harder to read and harder to extend:

```python
# Avoid
def process_payment(*, amount: Decimal, user: User) -> bool:
    if amount > 0:
        if user.is_active:
            # main logic deeply nested
            return True
        else:
            raise ValueError("User is not active")
    else:
        raise ValueError("Amount must be positive")

# Prefer
def process_payment(*, amount: Decimal, user: User) -> bool:
    if amount <= 0:
        raise ValueError("Amount must be positive")
    if not user.is_active:
        raise ValueError("User is not active")
    # main logic at the top indentation level
    return True
```

## Specific Exceptions

Catch the narrowest exception that the code can actually raise. `except Exception:` (let alone bare `except:`) swallows programming errors, `KeyboardInterrupt` semantics, and anything else that should have surfaced:

```python
# Avoid
try:
    user = User.objects.get(id=user_id)
except Exception:
    return None

# Prefer
try:
    user = User.objects.get(id=user_id)
except User.DoesNotExist:
    return None
```

Only catch `Exception` at process or task boundaries where re-raising would crash the worker — and even then, log with `logger.exception(...)` before re-raising or returning.

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

## No `from __future__ import annotations`

On Python 3.10+ projects (which is everything we work on), `from __future__ import annotations` is dead weight. PEP 604 (`str | None`) and PEP 585 (`list[int]`) work natively without postponed evaluation. Importing it adds noise and surprises readers who think it does something.

If you see it in an existing file, leave it alone unless you're touching that file's imports for another reason — don't sweep just for this.

## `@transaction.atomic` Decorator over Context Manager

Default to the decorator form:

```python
# Preferred
@transaction.atomic
def transfer_funds(*, from_id: int, to_id: int, amount: Decimal) -> None:
    ...
```

The context-manager form is for cases where the atomic block is genuinely a sub-section of a larger function (e.g. some setup logic that should not roll back, or a `savepoint=False` inner block). When the whole function should be atomic, the decorator is shorter and harder to get wrong.

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

## Docstrings

Short docstrings (one to two sentences) for anything worth documenting at all. Skip them for internal helpers, obvious methods, and anything where the name + signature already says it. Reach for the Google-style `Args:`/`Returns:` block only when arguments need real prose:

```python
def calculate_total(items: list[Item]) -> Decimal:
    """Sum the line total of all items, applying per-item discounts."""

def filter_queryset(queryset: QuerySet, search: str) -> QuerySet:
    """Filter queryset by a comma-separated search string.

    Args:
        queryset: The queryset to filter.
        search: Search terms separated by commas; each token is matched
            against `name__icontains` and `OR`ed together.

    Returns:
        The filtered queryset, ordered by the original ordering.
    """
```

Don't write docstrings that just restate the function name. See also the `ai-mannerisms` skill on unsolicited docstrings.

## Check the Library First

Before writing a custom wrapper, workaround, or compatibility shim around a third-party library, grep the library for an existing setting, hook, or typed API. The primitive you'd build is usually already there.

```bash
# Check the installed source
python -c "import some_lib; print(some_lib.__file__)"
rg -l 'def ' "$(python -c 'import some_lib, os; print(os.path.dirname(some_lib.__file__))')"

# Check docstrings / signatures for the operation you want
python -c "import some_lib; help(some_lib.Client)"
```

If after a real look the primitive is genuinely missing, then write the wrapper. The cost of one search is much smaller than the cost of maintaining a parallel implementation that diverges from the upstream API a year later. Applies equally to Python libraries and to Rust crates wrapped via PyO3 (check the crate's typed-command surface before calling `call_method` manually).

## Top-Level Imports by Default

Imports go at the top of the module. Function-local imports are an explicit signal: "this is here to break a circular import" or "this is heavy and only used on one rare path". Don't reach for them defensively.

```python
# Wrong (no circular-import reason, no perf reason)
def render_page(request):
    from django.template.loader import render_to_string
    return render_to_string("page.html")

# Right
from django.template.loader import render_to_string

def render_page(request):
    return render_to_string("page.html")
```

If a local import is needed, add a one-line comment explaining why.

## Per-Model Imports in Tests

In test files, import each model directly. Don't import the `models` module and access attributes off it.

```python
# Wrong
from myapp import models

def test_thing(db):
    obj = models.Thing.objects.create(name="x")

# Right
from myapp.models import Thing

def test_thing(db):
    obj = Thing.objects.create(name="x")
```

Per-model imports keep the test's surface area visible at the top of the file and make grep-driven refactors trivial.

---
