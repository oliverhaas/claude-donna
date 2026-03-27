---
name: django-save-hooks
description: Model save hooks with dirty tracking and bulk operation support. Use when adding save/post_save logic, bulk_create/bulk_update, or change-tracking to Django models.
user-invocable: false
---

# Model Save Hooks

Django's `bulk_create()` and `bulk_update()` bypass `.save()`. Use a service layer so business logic runs for both single and bulk saves.

## Service Layer

```python
class MyService:
    @staticmethod
    def entity_pre_save(*, entities: list["MyModel"]) -> None:
        # Validation, normalization, dirty-state capture
        BaseModelService.dirty_set_was_dirty(instances=entities)

    @staticmethod
    def entity_post_save(*, entities: list["MyModel"]) -> None:
        dirty = BaseModelService.dirty_filter_was_dirty(instances=entities)
        for entity in dirty:
            if "status" in entity.get_was_dirty_fields():
                # Handle status change
                pass
```

## Model Layer

Route single `.save()` through the same service functions:

```python
class MyModel(models.Model):
    @transaction.atomic
    def save(self, *args, pre_save: bool = True, post_save: bool = True, **kwargs) -> None:
        if pre_save:
            MyService.entity_pre_save(entities=[self])
        super().save(*args, **kwargs)
        if post_save:
            MyService.entity_post_save(entities=[self])
```

## Bulk Operations

```python
@transaction.atomic
def foo(entities: list[MyModel]) -> None:
    MyService.entity_pre_save(entities=entities)
    MyModel.objects.bulk_update(entities)
    MyService.entity_post_save(entities=entities)
```

## Dirty Field Tracking

This project uses the `django-filthyfields` package (a fork of django-dirtyfields) for change tracking. Models that inherit from its mixin provide:

- `is_dirty(check_relationship=False)` -- True if instance has unsaved changes
- `was_dirty(check_relationship=False)` -- True after save if instance had changes before that save
- `get_was_dirty_fields(check_relationship=False)` -- dict of fields that were dirty before save

Pass `check_relationship=True` to include FK field changes (no extra queries).

`BaseModelService` helpers for bulk operations:
- `dirty_set_was_dirty(instances=...)` -- call in pre_save to snapshot dirty state
- `dirty_filter_was_dirty(instances=...)` -- call in post_save to get only changed instances

---
