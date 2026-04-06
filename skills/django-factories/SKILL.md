---
name: django-factories
description: factory_boy patterns for test data. Use when writing, reviewing, or modifying factories.
user-invocable: false
---
# Factory Guidelines

## Field Coverage

Every required model field must have a corresponding factory entry. Handle optional fields appropriately:

```python
# Required field
name = factory.Faker("slug")

# Optional field (null=True): randomize presence
folder = factory.Maybe(
    factory.LazyFunction(lambda: random.random() > 0.5),
    yes_declaration=SubFactory(FolderFactory),
    no_declaration=None,
)

# File fields: use built-in django helpers
image = factory.django.ImageField()
```

## Uniqueness

Use `factory.Sequence` for fields with uniqueness constraints:

```python
username = factory.Sequence(lambda n: f"user_{n}")
slug = factory.Sequence(lambda n: f"{fake.slug()}_{n}")
email = factory.Sequence(lambda n: f"{fake.user_name()}_{n}@example.com")
```

## Conditional Fields

Use `factory.LazyAttribute` for fields that depend on other fields:

```python
extension = factory.LazyAttribute(
    lambda obj: fake.random_element(ImageExtensionChoices)
    if obj.type == Media.TypeChoices.IMAGE
    else fake.random_element(VideoExtensionChoices)
)
```

Use `factory.Maybe` for conditional population, and `class Params` for complex conditions:

```python
class Params:
    has_image = factory.LazyAttribute(
        lambda obj: obj.type == Media.TypeChoices.IMAGE
        or obj.status in [Media.StatusChoices.PROCESSED, Media.StatusChoices.VERIFIED]
    )

image = factory.Maybe(
    "has_image",
    yes_declaration=factory.django.ImageField(filename="test.webp"),
    no_declaration=None,
)
```

## Randomization

Pick from choice sets with `factory.Faker`:

```python
status = factory.Faker("random_element", elements=Media.StatusChoices)
```

Be careful: other fields may depend on the randomly assigned value:

```python
has_name = factory.Faker("boolean")
name = factory.Maybe("has_image", yes_declaration="John", no_declaration=None)
```


---
