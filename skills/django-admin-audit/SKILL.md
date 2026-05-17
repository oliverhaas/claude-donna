---
name: django-admin-audit
description: Audit every Django model in the project for admin registration and the common performance/UX footguns. Produces a single report grouped by issue type. Use when onboarding to an unfamiliar Django project or before a release.
user-invocable: true
---

# Django Admin Audit

Walk the project's models and check each one against the admin conventions in the `django-admin` skill. Collect issues, then print a single report grouped by issue type so they can be tackled one category at a time.

This skill is the audit procedure only. For the *why* behind each rule (`list_select_related` default-depth-5 gotcha, `autocomplete_fields` widget cost, `list_filter` safe-vs-unsafe types), read the `django-admin` skill first.

## Step 1: Discover All Models

```bash
grep -rn "class \w\+(.*Model\|.*BaseModel)" --include="*.py" \
  $(find . -type f \( -name "models.py" -o -path "*/models/*.py" \) | xargs -n1 dirname | sort -u)
```

Skip:
- Abstract models (`abstract = True` in `Meta`)
- Models in third-party packages (anything under `.venv/`, `site-packages/`)
- Auto-generated models from `inspectdb` if any (usually under `legacy/` or similar)

## Step 2: Check Admin Registration

For each model, search for registration:

```bash
grep -rn "@admin\.register([A-Za-z_]\+\b\|admin\.site\.register([A-Za-z_]\+\b" \
  --include="*.py" -l
```

Then for each match read the file and confirm the model is in the registration call. One admin file may register multiple models; don't assume one-file-per-model.

**Issue:** `Model {app}.{Model} is not registered in admin.`

## Step 3: Check `autocomplete_fields`

Every `ForeignKey` and `OneToOneField` on a registered model should be in `autocomplete_fields` (or `raw_id_fields` as a fallback when the target admin has no `search_fields`).

For each registered model:

```bash
grep -n "ForeignKey\|OneToOneField" path/to/model_file.py
grep -n "autocomplete_fields\|raw_id_fields" path/to/admin_file.py
```

Diff the FK/O2O field names against `autocomplete_fields + raw_id_fields`.

**Issue:** `Admin for {Model} is missing autocomplete_fields for: {field1}, {field2}.`

## Step 4: Check `search_fields`

Every admin class should define `search_fields` containing at least:
- `id`
- One human-readable field (`name`, `label`, `title`, `slug`, or similar)

**Issues:**
- `Admin for {Model} has no search_fields.`
- `Admin for {Model} is missing 'id' in search_fields.`
- `Admin for {Model} has no human-readable search field (name/label/title/slug).`

Skip this check if the admin is read-only or has fewer than ~5 fields total (low value).

## Step 5: Check `list_select_related`

Any FK referenced in `list_display` — bare name or `__` lookup — must be in `list_select_related`. With the default `list_select_related = False` and *any* FK in `list_display`, Django calls `qs.select_related()` with no arguments, which recursively follows every non-nullable FK up to `Query.max_depth = 5`.

For each registered model:

1. Read `list_display` from the admin class.
2. Identify which entries are FK fields on the model.
3. Also catch `__` lookups like `customer__email` (base field = `customer`).
4. Compare against `list_select_related`.

**Issue:** `Admin for {Model} uses FK fields in list_display without list_select_related: {field1}, {field2}.`

## Step 6: Check `list_filter`

`list_filter` renders every distinct value as a sidebar choice. Only safe on:

- `BooleanField`, `DateField`, `DateTimeField`
- Fields with `choices=`
- FKs to small, bounded tables (rarely; prefer `SimpleListFilter`)

Unsafe on unbounded `CharField` / `IntegerField`, or FKs to large tables.

For each entry in `list_filter`, resolve the full field path to its terminal field type. An entry like `customer__country` traverses `customer` (FK) -> `country` (CharField or FK). The terminal field is what matters.

**Issue:** `Admin for {Model} has high-cardinality field in list_filter: {field} (terminal type: {type}).`

## Output Format

Group issues by type, not by model:

```
## Missing Admin Registration (3)
- products.Variant
- orders.ReturnItem
- ...

## Missing autocomplete_fields (7)
- ProductAdmin: brand, category
- OrderAdmin: customer
- ...

## search_fields Issues (4)
- ProductAdmin: missing id
- VariantAdmin: no search_fields defined
- ...

## list_select_related Issues (3)
- OrderAdmin: customer in list_display but not in list_select_related
- ...

## list_filter Issues (2)
- ProductAdmin: name (CharField, unbounded)
- ...

## Summary
X models checked, Y issues found across Z categories.
```

If a category has zero issues, omit the heading rather than printing an empty section.

## Optional: Project-Specific Conventions

Some projects have additional admin conventions worth checking. Examples to look for and add to the audit if they apply:

- An auto-discovered test (e.g. `TestAllAdminViews`) that exercises every registered admin via factories. Flag models without matching `{ModelName}Factory`, or models in a `SKIP_FACTORIES` list.
- Multi-tenant search requirements (e.g. always include `tenant__name` or `merchant__name` in `search_fields` when the model has that FK).
- Custom `AdminSite` instances — only models registered with the custom site count.

These are project-specific. Don't apply them blindly; check the project's existing admin conventions first.
