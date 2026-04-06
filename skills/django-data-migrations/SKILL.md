---
name: django-data-migrations
description: Detecting when data migrations are needed for model and business logic changes. Use when changing model fields, defaults, or constraints that affect existing data.
user-invocable: false
---

# Data Migrations Review Guide

Missing data migrations are a common source of production bugs. Code changes pass all tests (against clean data) but break on existing data.

## When to Flag

### 1. Choice/Enum Value Changes
Renamed, removed, or restructured `TextChoices`/`IntegerChoices` values. Existing DB rows still hold the old string.
**Flag if**: No `RunPython` migration updates existing values.

### 2. New Required Fields or Relationships
Non-nullable fields/ForeignKeys added without a default.
**Flag if**: No migration to populate the field or create related objects for existing records.

### 3. New Database Constraints
`CheckConstraint`, `UniqueConstraint`, or `unique=True` added.
**Flag if**: No migration to clean existing data that would violate the constraint.

### 4. Changed Object Creation Timing
Code changes *when* or *where* related objects are created. Records already past that point may lack the relationship.
**Flag if**: No migration to backfill missing related objects.

### 5. State Machine Modifications
New/renamed/removed states, changed transitions, or new transition requirements.
**Flag if**: No migration to reconcile existing records with the new state machine.

### 6. Changed Business Logic Assumptions
Default value changes, new required conditions, or changed data formats.
**Flag if**: Existing data doesn't satisfy the new assumptions and there's no migration.

## Review Checklist

When the diff contains model/state/relationship changes, verify:

1. **Existing values valid?** Do all current DB values still fit new choices/constraints?
2. **Relationships intact?** Do existing records have all newly required relationships?
3. **States consistent?** Can existing records still transition in the new state machine?
4. **Assumptions hold?** Does existing data satisfy new business logic assumptions?
5. **Validation tightened?** Are new validators, constraints, or stricter field options being added? Existing data must comply before or alongside the migration.
6. **Migration present?** Is there a `RunPython` data migration for each concern above?

## What to Check in Data Migrations

When a data migration IS present, verify:

- Uses `apps.get_model()`, not current model imports
- Handles edge cases (None values, missing relationships, already-migrated records)
- Uses appropriate `Stage` (usually `Stage.POST_DEPLOY` from `django-syzygy`)
- Has a reverse operation (or explicit `migrations.RunPython.noop`)
- Includes verification (counts, assertions) for unexpected data
- Large datasets use `.iterator(chunk_size=...)` or bulk operations


---
