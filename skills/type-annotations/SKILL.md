---
name: type-annotations
description: Python type annotation patterns and pitfalls. Use when writing or reviewing type hints, configuring mypy/ty, or working with generics, protocols, or Django-typed code.
user-invocable: false
---

# Type Annotations

## Core Syntax Preferences

Use union syntax from Python 3.10+:

```python
# Preferred
def get_user(user_id: int) -> User | None: ...

# Avoid
from typing import Optional, Union
def get_user(user_id: int) -> Optional[User]: ...
```

Use built-in generic types directly (Python 3.9+):

```python
# Preferred
def process(items: list[str]) -> dict[str, int]: ...

# Avoid
from typing import List, Dict
def process(items: List[str]) -> Dict[str, int]: ...
```

## TYPE_CHECKING Imports

Use `TYPE_CHECKING` to avoid circular imports and expensive runtime imports. The imported names are only available to type checkers, not at runtime.

In Python 3.14+, annotations are evaluated lazily by default (PEP 649/749) - forward references work without string quotes and without `from __future__ import annotations`:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Article, Author
    from accounts.models import User


def create_article(*, author: Author, user: User) -> Article:
    ...
```

`TYPE_CHECKING` is still needed even in Python 3.14+ when the import would cause a circular import at runtime or when you want to avoid importing a heavy module at runtime. The deferred evaluation only helps with name resolution inside annotations - it does not execute the imports.

`from __future__ import annotations` is deprecated as of Python 3.14 (behavior is now the default) and will be removed once Python 3.13 reaches end-of-life in 2029. Don't add it to new files targeting Python 3.14+.

**On Python 3.12–3.13**: quote names from `TYPE_CHECKING` blocks when you don't have `from __future__ import annotations`:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Article


def create_article() -> "Article":  # quoted because Article not imported at runtime
    ...
```

## TypeVar, ParamSpec, TypeVarTuple

Prefer the Python 3.12+ `type` parameter syntax (PEP 695) for new code:

```python
# Generic function - new style (Python 3.12+)
def first[T](items: list[T]) -> T:
    return items[0]


# Generic class - new style
class Stack[T]:
    def push(self, item: T) -> None: ...
    def pop(self) -> T: ...


# Decorator that preserves the wrapped function's signature - new style
import functools
from typing import Callable

def retry[**P, T](func: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return func(*args, **kwargs)
    return wrapper
```

Legacy style (still valid, use when targeting Python < 3.12):

```python
from typing import TypeVar, ParamSpec, TypeVarTuple

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)  # for return types / read-only containers
T_contra = TypeVar("T_contra", contravariant=True)  # for write-only / callback inputs
P = ParamSpec("P")  # captures *args and **kwargs for decorators
Ts = TypeVarTuple("Ts")  # for variadic generics
```

Note: covariance/contravariance with PEP 695 syntax is inferred automatically by the type checker based on usage - no explicit markers needed. If you need to be explicit, use the legacy `TypeVar("T_co", covariant=True)` form.

## Protocols

Use protocols for structural (duck) typing instead of ABCs. They work without inheritance.

```python
from typing import Protocol, runtime_checkable


class Closeable(Protocol):
    def close(self) -> None: ...


class Readable(Protocol):
    def read(self, n: int = -1) -> bytes: ...


# runtime_checkable allows isinstance() checks, but only for method presence
@runtime_checkable
class Saveable(Protocol):
    def save(self) -> None: ...


def flush_and_close(resource: Closeable) -> None:
    resource.close()


# Any object with a .close() method works - no inheritance needed
flush_and_close(open("file.txt"))  # fine
```

Protocols with generics (Python 3.12+ syntax - variance is inferred by the type checker):

```python
from typing import Iterator, Protocol


class Container[T](Protocol):
    def __contains__(self, item: object) -> bool: ...
    def __iter__(self) -> Iterator[T]: ...
```

## Overloads

Use `@overload` when a function returns different types based on argument values or types. The overloads are type-checker-only; the actual implementation is undecorated and uses a broader signature.

```python
from typing import overload


@overload
def parse(value: str) -> int: ...
@overload
def parse(value: None) -> None: ...


def parse(value: str | None) -> int | None:
    if value is None:
        return None
    return int(value)


# Type checker knows: parse("42") -> int, parse(None) -> None
```

Common use case - different return types based on a flag:

```python
@overload
def get_items(*, as_queryset: Literal[True]) -> QuerySet[Item]: ...
@overload
def get_items(*, as_queryset: Literal[False] = ...) -> list[Item]: ...


def get_items(*, as_queryset: bool = False) -> QuerySet[Item] | list[Item]:
    qs = Item.objects.all()
    return qs if as_queryset else list(qs)
```

## Literal and TypeAlias

```python
from typing import Literal, TypeAlias

# Restrict to specific values
Status: TypeAlias = Literal["draft", "published", "archived"]

def set_status(status: Status) -> None: ...

# Type aliases for complex types
JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
```

Use `type` statement (Python 3.12+) instead of `TypeAlias`:

```python
type Status = Literal["draft", "published", "archived"]
type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
```

## TypeGuard

Use `TypeGuard` to narrow types inside conditionals:

```python
from typing import TypeGuard


def is_string_list(val: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(x, str) for x in val)


def process(items: list[object]) -> None:
    if is_string_list(items):
        # items is list[str] here
        print(items[0].upper())
```

## Callable Typing

```python
from typing import Callable

# Simple: Callable[[arg_types], return_type]
Handler = Callable[[int, str], bool]

# No args
Callback = Callable[[], None]

# Variadic (use ParamSpec for exact signature preservation)
from typing import ParamSpec
P = ParamSpec("P")
Decorator = Callable[[Callable[P, T]], Callable[P, T]]

# Protocol is clearer for complex callables
class ClickHandler(Protocol):
    def __call__(self, event: Event, *, propagate: bool = True) -> None: ...
```

## Django-Specific Typing

### QuerySet and Manager

Class base expressions (e.g. `QuerySet["Article"]`) are evaluated eagerly even in Python 3.14 - string quotes are still required there when the class is a forward reference. Method annotation forward references don't need quotes in Python 3.14+.

```python
from django.db import models
from django.db.models import QuerySet


class ArticleQuerySet(QuerySet["Article"]):  # base expr: quotes required
    def published(self) -> ArticleQuerySet:  # annotation: no quotes needed (3.14+)
        return self.filter(status="published")

    def by_author(self, author: Author) -> ArticleQuerySet:  # annotation: no quotes needed (3.14+)
        return self.filter(author=author)


class Article(models.Model):
    objects: models.Manager["Article"] = ArticleQuerySet.as_manager()  # type: ignore[assignment]
    ...
```

For custom managers:

```python
from django.db import models


class ArticleManager(models.Manager["Article"]):  # base expr: quotes required
    def get_queryset(self) -> QuerySet[Article]:  # annotation: no quotes needed (3.14+)
        return super().get_queryset().select_related("author")

    def published(self) -> QuerySet[Article]:  # annotation: no quotes needed (3.14+)
        return self.get_queryset().filter(status="published")


class Article(models.Model):
    objects = ArticleManager()
```

### Model Field Types

django-stubs maps model fields to Python types automatically. Key mappings:

```python
from django.db import models

class Article(models.Model):
    title: str          # CharField, TextField -> str (via django-stubs)
    count: int          # IntegerField -> int
    price: Decimal      # DecimalField -> Decimal
    created_at: datetime  # DateTimeField -> datetime
    author: Author      # ForeignKey -> instance type
    author_id: int      # ForeignKey -> _id suffix is int
    tags: ManyToManyField  # ManyToManyField[Tag, Tag]
```

### TypedDict for View Context / API Dicts

```python
from typing import TypedDict


class ArticleContext(TypedDict):
    article: Article
    can_edit: bool
    related: list[Article]


def article_detail(request: HttpRequest, pk: int) -> HttpResponse:
    context: ArticleContext = {
        "article": get_object_or_404(Article, pk=pk),
        "can_edit": request.user.has_perm("blog.change_article"),
        "related": list(Article.objects.published()[:3]),
    }
    return render(request, "article_detail.html", context)
```

## mypy vs ty

**mypy**: mature, widely used, slower, rich plugin ecosystem including django-stubs.
**ty**: Astral's type checker (10-60x faster than mypy). Reached beta in December 2025; stable release planned 2026. Django support is ongoing - if you rely on django-stubs, stick with mypy until ty's Django support stabilises.

### mypy Configuration (pyproject.toml)

```toml
[tool.mypy]
python_version = "3.14"
strict = true
plugins = ["mypy_django_plugin.main"]

[tool.django-stubs]
django_settings_module = "myapp.settings"

# Per-module overrides for third-party without stubs
[[tool.mypy.overrides]]
module = ["boto3.*", "botocore.*"]
ignore_missing_imports = true
```

`strict = true` enables: `--disallow-untyped-defs`, `--disallow-any-generics`, `--warn-return-any`, `--no-implicit-optional`, and more.

### ty Configuration

```toml
[tool.ty]
python-version = "3.14"
```

ty is strict by default and does not support mypy-style plugins - Django support is built in directly rather than via django-stubs. Key behavioral difference: ty treats missing return paths as errors where mypy with `--strict` may not, and ty resolves overloads differently.

### Common mypy Flags to Know

```toml
[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false  # relax in tests
```

```python
x = some_untyped_lib_call()  # type: ignore[no-untyped-call]
reveal_type(x)  # mypy prints inferred type during check - remove before committing
```

## Common Pitfalls

### Forward References in Annotations

In Python 3.14+, annotations are deferred - forward references just work:

```python
# Python 3.14+: fine as-is, no quoting or future import needed
class Node:
    def next(self) -> Node: ...
```

On Python 3.12-3.13, method annotations are still eagerly evaluated at class definition time, so `Node` isn't defined yet:

```python
# Python 3.12-3.13: NameError at runtime without one of these fixes

# Option 1: quote it
class Node:
    def next(self) -> "Node": ...

# Option 2: add future import (deprecated in 3.14, remove when upgrading)
from __future__ import annotations

class Node:
    def next(self) -> Node: ...
```

Note: class base expressions (e.g. `class Foo(Bar["Baz"])`) are evaluated eagerly in all Python versions, including 3.14. String quotes are still required there when `Baz` is a forward reference.

### Inspecting Annotations at Runtime (`annotationlib`)

Python 3.14 adds `annotationlib` for safely evaluating deferred annotations:

```python
import annotationlib

# Get annotations with different evaluation strategies
annotationlib.get_annotations(MyClass, format=annotationlib.Format.FORWARDREF)  # returns ForwardRef objects for unresolvable names
annotationlib.get_annotations(MyClass, format=annotationlib.Format.STRING)      # returns string representations
annotationlib.get_annotations(MyClass, format=annotationlib.Format.VALUE)       # evaluates fully (raises NameError on failure)
```

Use `annotationlib` instead of `typing.get_type_hints()` for new code on Python 3.14+. It handles deferred annotations correctly and gives control over evaluation strategy.

### Circular Imports

```python
# models.py imports from services.py; services.py imports from models.py -> circular
# Fix: put the import inside TYPE_CHECKING

# services.py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .models import Article  # only imported during type checking, not at runtime
```

### Mutable Default Arguments in Type Hints

```python
# This is a runtime bug AND a type issue
def append(item: int, lst: list[int] = []) -> list[int]:  # wrong
    lst.append(item)
    return lst

# Correct
def append(item: int, lst: list[int] | None = None) -> list[int]:
    if lst is None:
        lst = []
    lst.append(item)
    return lst
```

### Runtime vs Type-Time

`TYPE_CHECKING` is `False` at runtime. Code inside that block never runs. Only use it for imports used in annotations:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Article  # fine - only used in annotations

# Wrong: using Article at runtime inside TYPE_CHECKING block
if TYPE_CHECKING:
    from .models import Article

article = Article.objects.first()  # NameError at runtime - Article not imported
```

### `type: ignore` Abuse

Prefer fixing the underlying issue. Use `type: ignore` only for:
- Stubs not available for third-party package (`# type: ignore[import-untyped]`)
- Known false positive in the type checker
- Django ORM `objects` reassignment with custom manager (`# type: ignore[assignment]`)

Always include the specific error code, not bare `# type: ignore`.

## When NOT to Annotate

Skip annotations for:

- **Obvious local variables**: `x = 1`, `items = []` inside a function body - let the checker infer
- **Simple list/dict comprehensions**: type is obvious from context
- **Test helpers and fixtures** used only within tests: relax with `disallow_untyped_defs = false` in mypy config for `tests.*`
- **`__repr__`** and **`__str__`**: always returns `str`, no annotation needed in practice
- **Trivial private helpers** that are one-liners and only called once

Always annotate:
- All public function/method parameters and return types
- Module-level variables that aren't obviously typed
- Class attributes (especially in Django models and Pydantic models)
- Any function that crosses a module boundary

---
