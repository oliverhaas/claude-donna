---
name: type-annotations
description: Python type annotation patterns and pitfalls. Use when writing or reviewing type hints, configuring mypy/ty, or working with generics, protocols, or Django-typed code.
user-invocable: false
---

# Type Annotations

Assumes Python 3.14+ throughout (PEP 649/749 deferred annotations). Don't use `from __future__ import annotations` — it's deprecated in 3.14 and the behavior is now the default.

## TYPE_CHECKING Imports

Use `TYPE_CHECKING` to avoid circular imports and expensive runtime imports:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Article, Author
    from accounts.models import User


def create_article(*, author: Author, user: User) -> Article:
    ...
```

`TYPE_CHECKING` is still needed — deferred evaluation helps with name resolution in annotations but does not execute the imports at runtime.

## TypeVar, ParamSpec, TypeVarTuple

Use PEP 695 `type` parameter syntax:

```python
def first[T](items: list[T]) -> T:
    return items[0]


class Stack[T]:
    def push(self, item: T) -> None: ...
    def pop(self) -> T: ...


# Decorator preserving wrapped function's signature
import functools
from typing import Callable

def retry[**P, T](func: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return func(*args, **kwargs)
    return wrapper
```

For explicit variance (covariant/contravariant), use the legacy `TypeVar("T_co", covariant=True)` form — PEP 695 infers variance automatically.

## Protocols

Use protocols for structural (duck) typing instead of ABCs:

```python
from typing import Protocol, runtime_checkable


class Closeable(Protocol):
    def close(self) -> None: ...


@runtime_checkable  # allows isinstance() checks, but only for method presence
class Saveable(Protocol):
    def save(self) -> None: ...


def flush_and_close(resource: Closeable) -> None:
    resource.close()


flush_and_close(open("file.txt"))  # any object with .close() works
```

Protocols with generics:

```python
from typing import Iterator, Protocol


class Container[T](Protocol):
    def __contains__(self, item: object) -> bool: ...
    def __iter__(self) -> Iterator[T]: ...
```

## Overloads

Use `@overload` when return type depends on argument values/types:

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
```

Common use case — different return types based on a flag:

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

Prefer the `type` statement:

```python
type Status = Literal["draft", "published", "archived"]
type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
```

## TypeGuard

```python
from typing import TypeGuard


def is_string_list(val: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(x, str) for x in val)


def process(items: list[object]) -> None:
    if is_string_list(items):
        print(items[0].upper())  # items is list[str] here
```

## Callable Typing

```python
from typing import Callable

Handler = Callable[[int, str], bool]
Callback = Callable[[], None]

# Protocol is clearer for complex callables
class ClickHandler(Protocol):
    def __call__(self, event: Event, *, propagate: bool = True) -> None: ...
```

## Django-Specific Typing

### QuerySet and Manager

Class base expressions (e.g. `QuerySet["Article"]`) are evaluated eagerly even in 3.14 — string quotes are still required there for forward references.

```python
from django.db import models
from django.db.models import QuerySet


class ArticleQuerySet(QuerySet["Article"]):  # base expr: quotes required
    def published(self) -> ArticleQuerySet:
        return self.filter(status="published")

    def by_author(self, author: Author) -> ArticleQuerySet:
        return self.filter(author=author)


class Article(models.Model):
    objects: models.Manager["Article"] = ArticleQuerySet.as_manager()  # type: ignore[assignment]  # ty: ignore[invalid-assignment]
    ...
```

### Model Field Types

django-stubs maps model fields to Python types automatically:

```python
class Article(models.Model):
    title: str          # CharField, TextField -> str
    count: int          # IntegerField -> int
    price: Decimal      # DecimalField -> Decimal
    created_at: datetime  # DateTimeField -> datetime
    author: Author      # ForeignKey -> instance type
    author_id: int      # ForeignKey -> _id suffix is int
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

We run **both** type checkers. They catch different things:

- **mypy**: mature, slower, rich plugin ecosystem including django-stubs. Best Django support today.
- **ty**: Astral's type checker (10-60x faster). Django support ongoing but improving rapidly.

### mypy Configuration (pyproject.toml)

```toml
[tool.mypy]
python_version = "3.14"
strict = true
plugins = ["mypy_django_plugin.main"]

[tool.django-stubs]
django_settings_module = "myapp.settings"

[[tool.mypy.overrides]]
module = ["boto3.*", "botocore.*"]
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false  # relax in tests
```

### ty Configuration

```toml
[tool.ty]
python-version = "3.14"

[tool.ty.analysis]
# Don't respect mypy's `# type: ignore` comments — ty only checks `# ty: ignore`
respect-type-ignore-comments = false
```

ty is strict by default and does not support mypy-style plugins — Django support is built in directly. `respect-type-ignore-comments = false` is essential when running both checkers; without it, ty silently swallows errors that mypy's `# type: ignore` was suppressing.

## Common Pitfalls

### Forward References

Annotations are deferred in 3.14 — forward references just work. One exception: class base expressions are always evaluated eagerly, so quotes are still required there:

```python
class Node:
    def next(self) -> Node: ...  # fine

class ArticleQuerySet(QuerySet["Article"]):  # base expr: must quote
    ...
```

### `annotationlib`

Use `annotationlib` instead of `typing.get_type_hints()` for inspecting annotations at runtime:

```python
import annotationlib

annotationlib.get_annotations(MyClass, format=annotationlib.Format.FORWARDREF)
annotationlib.get_annotations(MyClass, format=annotationlib.Format.STRING)
annotationlib.get_annotations(MyClass, format=annotationlib.Format.VALUE)
```

### Circular Imports

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .models import Article  # only imported during type checking
```

### Suppression Comments

We use `# type: ignore[code]` for mypy and `# ty: ignore[code]` for ty. They are independent — each checker only reads its own comments.

Prefer fixing the underlying issue. Use suppression comments only for:
- Stubs not available for third-party package (`# type: ignore[import-untyped]`)
- Known false positive in the specific type checker
- Django ORM `objects` reassignment with custom manager (`# type: ignore[assignment]`)

Rules:
- Always include the specific error code — never bare `# type: ignore` or `# ty: ignore`
- Use the comment for the checker that produces the error. If both complain, use both: `# type: ignore[assignment]  # ty: ignore[invalid-assignment]`
- Error code names differ between checkers (e.g. mypy's `no-untyped-call` vs ty's `unresolved-reference`)
