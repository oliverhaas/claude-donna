---
name: api-clients
description: Guidelines for implementing API clients. Use when writing or reviewing code that calls external APIs.
user-invocable: false
---

# API Client Implementation Guidelines

## Core Requirements

- **Shared HTTP client base**: Build `httpx.Client` via a central `http` module: use `HttpClientConfig` and `HttpClientMultiton.get()` (or `HttpClientMultiton.build_client()` for one-off clients). Do not construct `httpx.Client(...)` directly in domain client bases.
- **Client reuse**: Prefer injecting an existing `http_client` into domain clients, or use `HttpClientMultiton.get(config)` so one client per (process, config) is reused. Do not create a new client per request or inside loops.
- **Client composition**: Domain-specific clients (e.g., `BrandsClient`) are composed in a main client
- **HTTP library**: Use `httpx`
- **Typing**: Full type hints everywhere

## HttpClientConfig and HttpClientMultiton

**Import**: `from core.http import HttpClientConfig, HttpClientMultiton`

### HttpClientConfig

Immutable, hashable dataclass used as the key for the multiton (same config = same shared client).

| Field | Type | Default | Purpose |
|-------|------|---------|--------|
| `name` | `str` | `""` | Identifier when multiple clients share similar config but need separate connection pools |
| `base_url` | `str` | `""` | Base URL prepended to all request paths |
| `timeout` | `float` | `60.0` | Seconds for connect/read/write/pool (use `httpx.Timeout` on the request for per-phase control) |
| `headers` | `tuple[tuple[str, str], ...]` | `()` | Default headers. Use tuple (hashable). Do not put per-request/per-thread values here -- pass them to `client.get(url, headers={...})` to avoid mutating shared state |
| `verify_ssl` | `bool` | `True` | TLS verification |
| `follow_redirects` | `bool` | `False` | Whether to follow HTTP 3xx |
| `auth` | `tuple[str, str] \| None` | `None` | HTTP Basic auth; for tokens use `headers` |
| `retries` | `int` | `0` | Count for `httpx.HTTPTransport(retries=...)` on transient network errors (ignored when `transport_cls` is set) |
| `transport_cls` | `type[httpx.BaseTransport] \| None` | `None` | Optional transport class (e.g. `httpx.HTTPTransport`, `RateLimitTransport`). When set, `transport_kwargs` must also be set. |
| `transport_kwargs` | `tuple[tuple[str, object], ...] \| None` | `None` | Optional tuple of `(key, value)` pairs passed to `transport_cls(**kwargs)`. When non-empty, `transport_cls` must also be set. All values must be hashable. |

- **`HttpClientConfig.build_transport() -> httpx.BaseTransport | None`**
  If `transport_cls` is set, returns `transport_cls(**dict(transport_kwargs))`; else if `retries` > 0, returns `httpx.HTTPTransport(retries=retries)`; else `None`.

### HttpClientMultiton

Returns a shared `httpx.Client` per `HttpClientConfig`. `get()` is thread-safe.

- **`get(config) -> httpx.Client`** -- Returns the shared client, creating if needed. Do not close manually; use `close_all()`.
- **`build_client(config) -> httpx.Client`** -- New client from config (no caching). Use for one-off or context-managed usage.
- **`close_all() -> None`** -- Closes all registered clients. Call in Celery `worker_process_init` (post-fork) and `worker_process_shutdown` / test teardown.

**Client reuse rules:**

- Use `HttpClientMultiton.get(config)` so connection pooling applies. Avoid one-off `httpx.get()` / `httpx.post()`.
- Do not create a new API client or raw `httpx.Client` inside loops or on every request.
- In tests, call `HttpClientMultiton.close_all()` in teardown to avoid leaking connections.

## Pydantic Models for API Clients

- **Pydantic v2 only**
- **Custom BaseModel**: All models must inherit from a custom `BaseModel` (see below)
- **Annotated fields**: Use `Annotated[..., Field(...)]` for every field
- **Validation**: Add robust validators; be strict for unreliable/temporary APIs
- **Union syntax**: Use `T | None` instead of `Optional[T]`
- **Metadata**: Add `description`; add `examples` when helpful; avoid trivial descriptions
- **Aliases**: Do not set explicit aliases; rely on `BaseModel.model_config` for snake_case <-> camelCase
- **Separation of concerns**: Separate request, response, query, and path parameter models

## Custom BaseModel (Pydantic v2)

```python
from typing import ClassVar
from pydantic import BaseModel as _PydanticBaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class BaseModel(_PydanticBaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="ignore",
        use_enum_values=True,
        ser_json_tuples=True,
    )
```

## Field authoring rules

- Always use `Annotated[T, Field(...)]`.
- Prefer precise types: `Literal`, `StrictStr`, `Annotated[str, Field(min_length=..., pattern=...)]`, `NonNegativeInt`, `PositiveInt`, etc.
- Prefer `Decimal` for money; avoid `float`.
- Use `T | None` instead of `Optional[T]`.
- Include `description`; add `examples` when helpful; avoid trivial descriptions.
- Avoid explicit `alias` in `Field`; rely on `alias_generator`.
- Use `field_validator`/`model_validator` for non-trivial constraints.
- Strictness policy: For request models, prefer `StrictInt`/`StrictStr`/`StrictBool` to fail fast on wrong inputs. For response models, use standard `int`/`str`/`bool` unless the provider is proven strict; then `Strict*` is fine.

## Validation strategy

- Stable APIs: sensible checks (lengths, enums, ranges).
- Unreliable/temporary APIs: validate inputs thoroughly to prevent invalid data causing problems downstream
- Requests vs responses: requests should be strict (`Strict*` types and stricter constraints). Responses can be tolerant to avoid false positive errors.

## Examples

```python
from typing import Annotated, ClassVar

import httpx
from pydantic import Field, field_validator, ConfigDict

from .base import BaseClient
from .models import BaseModel


class BrandCreateRequest(BaseModel):
    # Stricter for outbound payloads
    model_config: ClassVar[ConfigDict] = BaseModel.model_config | ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=120, description="Human-readable brand name", examples=["Acme"])]
    description: Annotated[str | None, Field(max_length=500, description="Optional marketing description")] = None
    website_url: Annotated[str | None, Field(pattern=r"^https?://", description="Public website starting with http/https") ] = None

    @field_validator("name")
    @classmethod
    def name_must_be_trimmed(cls, v: str) -> str:
        return v.strip()


class BrandResponse(BaseModel):
    id: Annotated[int, Field(description="Internal identifier", examples=[123])]
    name: Annotated[str, Field(description="Brand name")]
    description: Annotated[str | None, Field(description="Marketing description")] = None
    is_active: Annotated[bool, Field(description="Whether brand is active", examples=[True])]


class BrandsClient(BaseClient):
    def create(self, payload: BrandCreateRequest) -> BrandResponse:
        resp = self.http_client.post(
            self._url_with_path("/brands"),
            json=payload.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        resp.raise_for_status()
        return BrandResponse.model_validate(resp.json())

    def get(self, brand_id: int) -> BrandResponse:
        resp = self.http_client.get(self._url_with_path(f"/brands/{brand_id}"))
        resp.raise_for_status()
        return BrandResponse.model_validate(resp.json())
```

## Query and path parameter models

```python
from typing import Annotated
from pydantic import Field

from .models import BaseModel


class BrandQuery(BaseModel):
    search: Annotated[str | None, Field(max_length=120, description="Search term")] = None
    limit: Annotated[int | None, Field(ge=1, le=200, description="Page size", examples=[50])] = 50
    offset: Annotated[int | None, Field(ge=0, description="Offset for pagination", examples=[0])] = 0
```

## Testing

Keep API client tests simple; this catches ~99% of issues.

- **Model examples**: Provide at least one valid example JSON per important model (prefer real-world payloads anonymized; production-derived is ideal). Optionally add multiple valid examples and a few invalid ones.
  - Validate via `Model.model_validate(example_json)`; assert key fields and types.
  - Minimal test shape (auto-discover examples by model name):

```python
import pytest
from pathlib import Path
from pydantic import ValidationError

from tests.utils import load_model_json_examples
from api_client.models import BrandResponse  # add your models

MODELS = [BrandResponse]

def test_model_examples_validate() -> None:
    base_dir = Path(__file__).parent
    for model in MODELS:
        examples = load_model_json_examples(model=model, dir=base_dir)
        for _, json_str in examples["valid"].items():
            model.model_validate_json(json_str)
        for _, json_str in examples["invalid"].items():
            with pytest.raises(ValidationError):
                model.model_validate_json(json_str)
```

- **Client call wiring**: Patch the relevant `httpx.Client` method and assert:
  - Correct URL/path/params formatting
  - Serialized JSON/body is from `model_dump(mode="json", by_alias=True, exclude_none=True)` (or files/form for multipart)
  - Headers/auth present
- **Auth**: Add one unit test checking auth headers are set/applied as expected.

## Notes

- When serializing for requests, almost always use `model_dump(mode="json", by_alias=True, exclude_none=True)`.
- For PATCH-like updates, consider `exclude_unset=True`.
- For responses, prefer `Model.model_validate(response.json())` and strong types.
- If the remote API uses different casing, rely on `alias_generator`; do not manually add `alias` per field unless absolutely required.
- Use `Enum` types and `use_enum_values=True` in `model_config`.
- Use timezone-aware `datetime` where possible. 

---
