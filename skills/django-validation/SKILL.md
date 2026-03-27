---
name: django-validation
description: Django multi-layer validation strategy and Pydantic API patterns. Use when adding validation to models, forms, or APIs.
user-invocable: false
---

# Data Validation Layers

## Decision Tree: Which Layer Validates What

1. **Database constraints** (strongest guarantee) -- unique, check constraints, field types. Enforced even for raw SQL.
2. **Django model fields + validators** -- field-level rules (length, format, range). Use `clean()` for cross-field validation and normalization.
3. **Forms (UI path)** -- UI-specific rules. ModelForm calls `full_clean()` automatically.
4. **Pydantic (API path)** -- request validation. Must match Django model constraints.
5. **Service layer** -- orchestrates `full_clean()` + save + side effects. DB queries live here, not in validators.

Validation flow:
- API: Pydantic -> Service -> `full_clean()` -> save
- UI simple: Form -> Service -> save
- UI complex: Form -> Service(s) -> `full_clean()` -> save

## full_clean() Warnings

`save()` does NOT call validation. Always call `full_clean()` before `save()` when not using forms:

```python
instance.full_clean()  # clean_fields() -> clean() -> validate_unique() -> validate_constraints()
instance.save()
```

Transformation rules:
- Field validators: validate only, no transformation
- Model/Form `clean()`: can transform (strip, lowercase)
- Pydantic validators: can transform

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

## Model clean()

```python
def clean(self):
    if self.name:
        self.name = self.name.strip()
    if self.is_active and not self.price:
        raise ValidationError('Active products must have a price')
```

## Pydantic for Django Ninja APIs

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

Request models -- match Django field constraints:

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

Endpoint pattern -- extract primitives, never pass Pydantic model to service:

```python
@router.post("/products/", response=ProductResponse)
def create_product(request, data: CreateProductRequest) -> ProductResponse:
    product = product_create(
        name=data.name,
        category_id=data.category_id,
        price=data.price,
        merchant=request.user.merchant,
    )
    return ProductResponse.from_django_model(product)
```

Pydantic rules: use `Annotated[T, Field(...)]`, `str | None` not `Optional[str]`, `field_validator` (v2 not `validator`), add `Field(description="...")` for docs.

---
