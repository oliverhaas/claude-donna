---
name: django-views
description: Encode shareable view state (filters, search, sort) in URL query parameters. Use when adding filtering, searching, sorting, or pagination to views.
user-invocable: false
---

# View State in URL Query Parameters

Encode shareable view state (filters, search, sort, pagination, active tabs) in URL query parameters so state survives refreshes, is bookmarkable, and works with browser navigation.

**Belongs in query params:** filters, search, sort, pagination, date ranges, active tab, timeframe
**Does NOT belong:** large data sets (use `request.session`), sensitive data, temporary UI-only state (modals, tooltips), write operations

## Reading Params

```python
# Single value with default
status = request.GET.get("status", Product.Status.ACTIVE)
sort = request.GET.get("sort", "-created_at")

# Multi-value
countries = request.GET.getlist("country")
```

Always pass every read param into the template context so templates can preserve it.

## Preserving Params

**Hidden form inputs** — carry non-form state so it's included in the next request:
```html
<form hx-get="{% url 'products_list' %}" hx-replace-url="true">
    <input type="hidden" value="{{ status }}" name="status" />
    <input type="hidden" value="{{ sort }}" name="sort" />
</form>
```

**`add_param` tag** (`templatetags/common.py`) — set/override one param, preserve all others:
```html
{% load common %}
<a href="{% add_param request.get_full_path 'page' page_obj.next_page_number %}">Next</a>
```

**In Python** — use `build_url_with_params` (`utils/url_utils.py`) or `request.GET.dict().copy()` + `urlencode`.

## HTMX

- Always use `hx-replace-url="true"` on any element that changes view state
- Use `hx-params="*"` to forward all params, or `hx-include` for selective inclusion
- For simple toggles, inline params: `hx-get="?tab={{ tab }}&timeframe_days={{ days }}"`

## Checklist for New Views

1. Read all params from `request.GET` with sensible defaults
2. Pass every param into the template context
3. Use `hx-replace-url="true"` on state-changing HTMX elements
4. Carry non-visible state as hidden inputs
5. Use `add_param` for pagination links
6. Reset `page` to 1 when filters change
