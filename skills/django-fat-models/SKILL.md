---
name: django-fat-models
description: Fat model pattern with custom querysets. Use when business logic is entity-centric and doesn't cross model boundaries.
user-invocable: false
---

# Fat Models Pattern

For simpler projects or entity-centric logic, fat models with custom querysets are sufficient. No need for a service layer when logic doesn't cross model boundaries or coordinate external systems.

## When to Use Fat Models vs. Services

- **Fat models**: Logic belongs to a single entity. Validation, state transitions, computed properties, scoped queries.
- **Services** (see `django-services` skill): Logic orchestrates multiple models, calls external systems, or coordinates cross-cutting operations.

Start with fat models. Extract to services when complexity demands it.

## Model Methods for Business Logic

```python
class Order(models.Model):
    status = models.CharField(max_length=20, default="draft")
    submitted_at = models.DateTimeField(null=True, blank=True)
    items = models.ManyToManyField("Product", through="OrderLine")

    def submit(self):
        """Transition to submitted state."""
        if self.status != "draft":
            raise ValidationError("Only draft orders can be submitted.")
        self.status = "submitted"
        self.submitted_at = timezone.now()
        self.full_clean()
        self.save()

    def cancel(self):
        if self.status not in ("draft", "submitted"):
            raise ValidationError("Cannot cancel a completed order.")
        self.status = "cancelled"
        self.full_clean()
        self.save()

    @property
    def total(self) -> Decimal:
        return self.lines.aggregate(total=Sum(F("qty") * F("unit_price")))["total"] or Decimal("0")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
```

## Custom QuerySet / Manager

```python
class OrderQuerySet(models.QuerySet):
    def active(self):
        return self.exclude(status="cancelled")

    def overdue(self):
        cutoff = timezone.now() - timedelta(days=30)
        return self.filter(status="submitted", submitted_at__lt=cutoff)

    def with_totals(self):
        return self.annotate(total=Sum(F("lines__qty") * F("lines__unit_price")))

class Order(models.Model):
    objects = OrderQuerySet.as_manager()
    # ... fields ...
```

Usage: `Order.objects.active().overdue().with_totals()`

## Guidelines

1. Call `full_clean()` in `save()` to enforce model-level validation consistently
2. State transitions (submit, cancel, approve) belong on the model as methods
3. Computed properties use `@property` for single-instance, QuerySet annotations for bulk
4. Custom QuerySet methods are chainable and composable -- prefer them over raw filters in views
5. Keep model files focused. If a model file grows past ~300 lines, consider splitting logic or moving to services

---
