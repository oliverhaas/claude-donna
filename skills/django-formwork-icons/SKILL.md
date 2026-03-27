---
name: django-formwork-icons
description: Icon usage in django-formwork widgets. Use when adding icons to SearchSelect, MultiSelect, ComboBox, or similar widgets.
user-invocable: false
---

# Icons in django-formwork Widgets

Icons are passed directly to widgets as inline SVG, emoji, or HTML strings. There is no dedicated icon storage or component system.

## Widget `icons` Parameter

Pass an `icons` dict mapping choice values to icon strings:

```python
from django.utils.safestring import mark_safe
from formwork.widgets import SearchSelect, MultiSelect, ComboBox

class MyForm(forms.Form):
    status = forms.ChoiceField(
        choices=[("active", "Active"), ("archived", "Archived")],
        widget=SearchSelect(
            icons={
                "active": mark_safe('<svg xmlns="http://www.w3.org/2000/svg" ...>...</svg>'),
                "archived": mark_safe("&#128230;"),  # or emoji/HTML
            }
        ),
    )
```

Always wrap icon values in `mark_safe()` to prevent auto-escaping.

## Server-Side Search: `icon_from_instance`

For widgets with server-side search (no static choices), use the `icon_from_instance` callback:

```python
widget = SearchSelect(
    search_url=reverse_lazy("api:user-search"),
    icon_from_instance=lambda obj: mark_safe(f'<img src="{obj.avatar_url}" class="size-5 rounded-full">'),
)
```

The callback receives a model instance and must return a `mark_safe()` string.

## How Icons Render

Icons are injected into dropdown templates via Alpine.js `x-html` binding, which renders raw HTML. This is why `mark_safe()` is required -- without it, the HTML is escaped to text.

## Guidelines

- Use inline SVG for custom icons, emoji for quick placeholders
- Keep SVGs small; strip unnecessary attributes
- `mark_safe()` is mandatory for all icon values
- `icon_from_instance` is for server-side search only; static choices use the `icons` dict

---
