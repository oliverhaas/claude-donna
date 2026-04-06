---
name: python-data-containers
description: Data container types (dataclass, NamedTuple, TypedDict, Pydantic) and when to use each. Use when choosing or creating a data structure for passing structured data.
user-invocable: false
---

# Data Containers

Prefer fewer container types to keep the codebase consistent and boilerplate low.

## Priority order

1. **Django Models** -- The main container. Persistent data lives here. Pass model instances directly. Used literally everywhere to keep boilerplate low.
2. **Pydantic Models** -- Usually API layer only, but there extensively. Use heavy validation and not just plain field definitions.
3. **Primitives** -- What services try to use to stay general. `str`, `int`, `Decimal`, `datetime`, `list`, `tuple`. Most reusable, no coupling.
4. **Dict and TypedDict** -- Dicts are unavoidable, and TypedDict adds safety. No runtime overhead, easily serializable. Use TypedDict over bare `dict` regularly.

## Try to avoid

`dataclass`, `NamedTuple`, custom classes, etc.: All great in general, but they have their own quirks and we want to keep the convention in this project simple. Avoid these.


---
