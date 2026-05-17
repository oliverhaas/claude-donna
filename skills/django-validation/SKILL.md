---
name: django-validation
description: Django multi-layer validation strategy and Pydantic API patterns. Use when adding validation to models, forms, or APIs.
user-invocable: false
---

# Data Validation Layers

## Decision Tree: Which Layer Validates What

1. **Database constraints** (strongest guarantee): unique, check constraints, field types. Enforced even for raw SQL.
2. **Django model fields + validators**: field-level rules (length, format, range). Use `clean()` for cross-field validation and normalization.
3. **Forms (UI path)**: UI-specific rules. ModelForm calls `full_clean()` automatically.
4. **Pydantic (API path)**: request validation. Must match Django model constraints.
5. **Service layer**: orchestrates `full_clean()` + save + side effects. DB queries live here, not in validators.

Validation flow:
- **API:** Pydantic → Service → `full_clean()` → save
- **UI simple:** Form → Service → save
- **UI complex:** Form → Service(s) → `full_clean()` → save

## Field Choice

Prefer specific field types over generic ones — they encode validation:

- `EmailField`, `URLField`, `SlugField`, `UUIDField`
- `PositiveIntegerField`, `PositiveSmallIntegerField`
- `DecimalField(max_digits=..., decimal_places=...)` for money (never `FloatField`)

Use `max_length`/`min_length`, `max_value`/`min_value`, `choices=`, `blank=False`, `null=False`, `unique=True` as appropriate.

Avoid `JSONField` for data with a stable schema — use structured fields so validation, constraints, and indexes actually apply. Use `JSONField` only for genuinely free-form payloads.

## `full_clean()` Warnings

`save()` does NOT call validation. Always call `full_clean()` before `save()` when not using forms:

```python
instance.full_clean()  # clean_fields() -> clean() -> validate_unique() -> validate_constraints()
instance.save()
```

Transformation rules:
- Field validators: validate only, no transformation.
- Model/Form `clean()`: can transform (strip, lowercase).
- Pydantic validators: can transform.

## Database Constraints

```python
class Meta:
    constraints = [
        models.UniqueConstraint(fields=['merchant', 'sku'], name='unique_merchant_sku'),
        models.CheckConstraint(
            check=models.Q(end_date__gte=models.F('start_date')),
            name='end_date_after_start_date',
        ),
    ]
```

For `TextChoices`/`IntegerChoices`, optionally back the field with a `CheckConstraint` so raw SQL writes can't bypass the choice set:

```python
class StatusChoices(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'

status = models.CharField(choices=StatusChoices.choices)

class Meta:
    constraints = [
        models.CheckConstraint(check=models.Q(status__in=StatusChoices.values), name='valid_status'),
    ]
```

Constraint violations are surfaced as `ValidationError` by `validate_constraints()`, with no runtime overhead vs app-level checks.

## Field Validators

```python
from django.core.validators import MinLengthValidator, RegexValidator

slug = models.CharField(
    max_length=50,
    validators=[
        MinLengthValidator(3),
        RegexValidator(r'^[a-z0-9-]+$', 'Only lowercase, numbers, hyphens'),
    ],
)
```

Custom reusable validators are plain callables that raise `ValidationError`:

```python
from django.core.exceptions import ValidationError
from django.utils import timezone

def validate_future_date(value):
    if value <= timezone.now().date():
        raise ValidationError('Date must be in the future')
```

Field validators run *first* during `full_clean()`. Keep them pure — no DB queries, no transformation.

## Model `clean()`

Cross-field validation and normalization belong here:

```python
def clean(self):
    if self.name:
        self.name = self.name.strip()
    if self.sku:
        self.sku = self.sku.upper()

    if self.is_active and not self.price:
        raise ValidationError('Active products must have a price')
    if self.sale_price and self.sale_price >= self.price:
        raise ValidationError('Sale price must be less than regular price')
```

## Forms (UI Path)

`ModelForm` runs model validation automatically (calls `full_clean()` on save) and gives you per-field `clean_<field>` hooks for UI-specific rules:

```python
class ProductForm(forms.ModelForm):
    def clean_sku(self):
        sku = self.cleaned_data['sku']
        if not sku.startswith(self.request.user.merchant.code):
            raise ValidationError('SKU must start with merchant code')
        return sku.upper()
```

Transformation in `clean_<field>` and `clean()` is fine; field validators stay pure.

## Pydantic for Django Ninja APIs

Core principles:

1. **API validation only** — never use Pydantic for Django forms or internal logic.
2. **No database queries in validators** — schema validation must be pure; move DB checks to the service layer.
3. **Validation parity** — Pydantic must match the Django model.
4. **Service layer separation** — extract primitives from Pydantic models before passing to services.

Base model with camelCase aliasing:

```python
class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        validate_assignment=True,
        extra="ignore",
    )
```

Request model:

```python
class CreateProductRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    category_id: Annotated[int, Field(gt=0)]
    price: Annotated[Decimal, Field(gt=0, decimal_places=2)]
    description: Annotated[str | None, Field(max_length=1000)] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode='after')
    def validate_pricing(self) -> 'CreateProductRequest':
        if self.sale_price and self.sale_price >= self.price:
            raise ValueError('Sale price must be less than regular price')
        return self
```

Endpoint pattern (extract primitives, never pass the Pydantic model to the service):

```python
@router.post("/products/", response=ProductResponse)
def create_product(request, data: CreateProductRequest) -> ProductResponse:
    product = ProductService.product_create(
        name=data.name,
        category_id=data.category_id,
        price=data.price,
        merchant=request.user.merchant,
    )
    return ProductResponse.model_validate(product)
```

Pydantic rules: `Annotated[T, Field(...)]` for every field, `str | None` not `Optional[str]`, `field_validator` (v2) not `validator`, add `Field(description="...")` for the OpenAPI docs.

### Validation Parity Cheatsheet

Pydantic constraints must match the underlying Django field. The shape of the mapping is mechanical:

| Django                                                       | Pydantic                                                        |
|--------------------------------------------------------------|-----------------------------------------------------------------|
| `CharField(max_length=255, validators=[MinLengthValidator(1)])` | `Annotated[str, Field(min_length=1, max_length=255)]`           |
| `EmailField()`                                               | `EmailStr`                                                      |
| `URLField()`                                                 | `Annotated[str, Field(pattern=r'^https?://')]` or `HttpUrl`     |
| `ForeignKey('Category', on_delete=...)`                      | `Annotated[int, Field(gt=0)]` for the id                        |
| `DecimalField(max_digits=10, decimal_places=2)`              | `Annotated[Decimal, Field(gt=0, decimal_places=2)]`             |
| `PositiveIntegerField()`                                     | `NonNegativeInt` or `Annotated[int, Field(ge=0)]`               |
| `BooleanField(default=False)`                                | `bool = False`                                                  |
| `choices=StatusChoices.choices`                              | `Literal[*StatusChoices.values]` or the enum directly           |
| `null=True`                                                  | `T | None = None`                                               |
| `unique=True`                                                | (not expressible in Pydantic — enforce in service / DB)         |

When the Django model tightens (new validator, stricter `max_length`), tighten Pydantic in the same commit; mismatches lead to "passes API validation, fails on save" or vice versa.

## Common Pitfalls

- **Forgetting `full_clean()`** when creating instances outside a `ModelForm`.
- **Mismatched validation** between Pydantic and the Django model — one tightens, the other doesn't.
- **Transforming in field validators** (move to `clean()` / Pydantic `field_validator`).
- **DB queries inside Pydantic validators** — those belong in the service layer, not the schema.
- **Using `JSONField` for data with a known schema** — you lose constraints, indexes, and validation.
- **No DB constraints** for critical business rules — app-level checks alone don't protect against raw SQL or concurrent writers.
