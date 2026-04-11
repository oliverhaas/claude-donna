---
name: django-jinja2
description: Jinja2 authoring patterns for Django. Use when writing new Jinja2 templates, configuring the Jinja2 environment, adding custom filters/globals, or deciding between Jinja2 and DTL.
user-invocable: false
---

# Django Jinja2

Authoring Jinja2 templates in Django. Covers environment setup, differences from DTL, filters/globals, macros, and integration with Django's staticfiles and URL reversing.

For converting existing DTL templates to Jinja2, use the `django-jinjafy` skill instead.

---

## When to Use Jinja2 vs DTL

**Use Jinja2 when:**
- New project with no legacy template burden
- Heavy use of macros or reusable template components
- You want real Python expressions in templates (`{{ 1 + 2 }}`, `{{ obj.method() }}`)
- You need a shared macro library across many templates
- Performance is critical (Jinja2 is ~2-10x faster than DTL for complex templates)

**Stay on DTL when:**
- You're using Django admin (admin templates are DTL-only)
- Your team is new to Django; DTL's restrictions prevent common mistakes
- You rely heavily on third-party apps whose templates are DTL (mixing is possible but messy)

**Mixing:** Django supports both in the same project via `TEMPLATES`. DTL and Jinja2 templates cannot extend each other — keep them in separate directories.

---

## Environment Setup

### Minimal TEMPLATES config

```python
# settings.py
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "DIRS": [BASE_DIR / "templates" / "jinja2"],
        "APP_DIRS": True,  # loads from <app>/jinja2/ directories
        "OPTIONS": {
            "environment": "myproject.jinja2_env.environment",
        },
    },
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates" / "django"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
```

With `APP_DIRS: True`, Jinja2 searches `<app>/jinja2/` directories. DTL searches `<app>/templates/`. These do not conflict.

### Custom Environment

Always define a custom environment function. This is where you register filters, globals, and extensions.

```python
# myproject/jinja2_env.py
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from jinja2 import Environment


def environment(**options) -> Environment:
    env = Environment(**options)

    env.globals.update(
        static=staticfiles_storage.url,
        url=reverse,
    )

    # Optional: mark_safe interop so Django's SafeString isn't double-escaped
    from django.utils.safestring import SafeData
    from jinja2 import Markup
    if not hasattr(SafeData, "__html__"):
        SafeData.__html__ = lambda self: str(self)

    return env
```

Reference it in `OPTIONS["environment"]` as shown above.

---

## Key Differences from DTL

### Auto-call

DTL auto-calls callables; Jinja2 does not.

```html
{# DTL: calls get_full_name() automatically #}
{{ user.get_full_name }}

{# Jinja2: you must call explicitly #}
{{ user.get_full_name() }}
```

**This is the #1 source of bugs when mixing or migrating.** `{{ obj.method }}` in Jinja2 renders `<bound method ...>`.

### Expressions

Jinja2 supports real Python-like expressions:

```html
{{ items|length > 0 }}
{{ price * quantity }}
{{ "yes" if is_active else "no" }}
{{ [1, 2, 3]|join(", ") }}
```

### Filter syntax

DTL uses `:` for filter arguments; Jinja2 uses `()`:

```html
{# DTL #}
{{ value|default:"n/a" }}
{{ value|truncatewords:30 }}

{# Jinja2 #}
{{ value|default("n/a") }}
{{ value|truncatewords(30) }}
```

### Variable scoping in blocks

`{% set %}` in Jinja2 is **block-scoped**. Variables set inside `{% for %}` or `{% if %}` are not visible outside:

```html
{# This does NOT work — x is scoped to the for block #}
{% set x = "" %}
{% for item in items %}
    {% set x = item.name %}
{% endfor %}
{{ x }}  {# still "" #}

{# Use namespace() to work around block scoping #}
{% set ns = namespace(x="") %}
{% for item in items %}
    {% set ns.x = item.name %}
{% endfor %}
{{ ns.x }}
```

### `{% with %}` has no block form

```html
{# DTL #}
{% with total=items|length %}{{ total }}{% endwith %}

{# Jinja2 — set is inline, no endwith #}
{% set total = items|length %}
{{ total }}
```

---

## Template Inheritance

Works the same as DTL conceptually, with minor syntax differences.

```html
{# base.html #}
<!DOCTYPE html>
<html>
<head>
  <title>{% block title %}My Site{% endblock %}</title>
</head>
<body>
  {% block content %}{% endblock %}
</body>
</html>
```

```html
{# page.html #}
{% extends "base.html" %}

{% block title %}Home — {{ super() }}{% endblock %}

{% block content %}
  <h1>Welcome</h1>
{% endblock %}
```

`super()` replaces `{{ block.super }}` from DTL.

Block names **cannot contain hyphens** in Jinja2. Use underscores: `{% block nav_sidebar %}`.

---

## Staticfiles and URL Reversing

Register `static` and `url` in your environment globals (shown above). Usage:

```html
<link rel="stylesheet" href="{{ static('css/main.css') }}">
<script src="{{ static('js/app.js') }}"></script>

<a href="{{ url('myapp:detail', pk=obj.pk) }}">View</a>
<form action="{{ url('myapp:create') }}" method="post">
```

`url()` maps directly to Django's `reverse()`. Named URL arguments work as keyword args.

For URL generation that may fail silently (e.g., optional links), wrap in a try/except in a global helper rather than letting `NoReverseMatch` bubble up to templates.

---

## Custom Filters

Register on `env.filters`. Filters are plain callables:

```python
# myproject/jinja2_env.py
from django.utils.html import format_html
from jinja2 import Markup


def currency(value, symbol="$") -> str:
    return f"{symbol}{value:,.2f}"


def highlight(text: str, query: str) -> Markup:
    """Wrap matched text in <mark>. Returns Markup to prevent double-escaping."""
    if not query:
        return Markup(text)
    escaped = text.replace(query, f"<mark>{query}</mark>")
    return Markup(escaped)


def environment(**options) -> Environment:
    env = Environment(**options)
    env.filters["currency"] = currency
    env.filters["highlight"] = highlight
    # ...
    return env
```

```html
{{ product.price|currency }}
{{ product.name|highlight(search_query) }}
```

**Escaping rule**: if your filter returns HTML, wrap the return value in `Markup`. Jinja2 will not double-escape `Markup` instances.

---

## Custom Globals

Globals are functions or values available in every template without being in the context:

```python
def environment(**options) -> Environment:
    env = Environment(**options)
    env.globals.update(
        static=staticfiles_storage.url,
        url=reverse,
        now=datetime.now,           # callable — call with {{ now() }}
        SITE_NAME="My Project",     # constant — use with {{ SITE_NAME }}
    )
    return env
```

Use globals for site-wide constants and utility functions. Do not duplicate what belongs in the request context (e.g., `request.user`).

---

## Extensions

Jinja2 extensions add new tags. Enable via `OPTIONS["extensions"]` or pass to `Environment`:

```python
OPTIONS = {
    "environment": "myproject.jinja2_env.environment",
    "extensions": [
        "jinja2.ext.i18n",    # {% trans %} / {% blocktrans %}
        "jinja2.ext.debug",   # {% debug %} dumps context
    ],
}
```

### i18n extension

```python
# jinja2_env.py
from django.utils.translation import gettext, ngettext

def environment(**options) -> Environment:
    env = Environment(**options)
    env.install_gettext_callables(gettext, ngettext, newstyle=True)
    return env
```

```html
{% trans %}Hello, world!{% endtrans %}
{% trans count=items|length %}
    {{ count }} item
{% pluralize %}
    {{ count }} items
{% endtrans %}
```

---

## Macros

Macros are reusable template functions. Define them in a shared file and import them.

```html
{# macros/forms.html #}
{% macro field(bf) %}
<div class="field{% if bf.errors %} field--error{% endif %}">
  {{ bf.label_tag() }}
  {{ bf }}
  {% if bf.errors %}
    <ul class="errors">
      {% for error in bf.errors %}
        <li>{{ error }}</li>
      {% endfor %}
    </ul>
  {% endif %}
  {% if bf.help_text %}
    <p class="help">{{ bf.help_text }}</p>
  {% endif %}
</div>
{% endmacro %}

{% macro submit(label="Submit", css_class="btn btn-primary") %}
<button type="submit" class="{{ css_class }}">{{ label }}</button>
{% endmacro %}
```

```html
{# myapp/templates/jinja2/myapp/form.html #}
{% from "macros/forms.html" import field, submit %}

<form method="post" action="{{ url('myapp:create') }}">
  {{ csrf_input }}
  {% for bf in form %}
    {{ field(bf) }}
  {% endfor %}
  {{ submit("Save") }}
</form>
```

Macros **cannot access the outer template context** by default. Pass values explicitly as arguments or use `{% macro foo() %}{% set bar = caller.bar %}` patterns. To access the caller's context, use `caller` (advanced) or just pass everything as args.

If a macro calls Django methods on its arguments (like `bf.label_tag()`), remember Jinja2 does not auto-call — use `()` explicitly.

---

## CSRF

Jinja2 does not have `{% csrf_token %}`. Use the `csrf_input` variable provided by Django's CSRF middleware:

```html
<form method="post">
  {{ csrf_input }}
  ...
</form>
```

`csrf_input` renders a `<input type="hidden" ...>` tag as a `Markup` string. It is automatically available in the template context when `django.middleware.csrf.CsrfViewMiddleware` is active.

---

## Performance Notes

- Jinja2 compiles templates to Python bytecode and caches them. In production (`DEBUG=False`), templates are compiled once on first render.
- Jinja2 is generally 2-10x faster than DTL for templates with complex logic, loops, and many variable lookups.
- DTL overhead is mostly in tag resolution and the context stack. Jinja2's compiled bytecode eliminates this.
- For extremely hot paths, consider moving rendering to the view layer using Python string formatting or `format_html`.
- Do not put slow logic in template globals or filters — they run per-render, not per-request.

---

## Common Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| `<bound method ...>` in output | Missing `()` on method call | Add `()`: `{{ obj.method() }}` |
| Double-escaped HTML (`&amp;lt;`) | `SafeString` not recognized | Patch `SafeData.__html__` in env setup |
| Variable not updated after loop | Block scoping | Use `namespace()` |
| `TemplateSyntaxError: expected name` | Block name has hyphen | Replace hyphens with underscores |
| `NoReverseMatch` crashes template render | Bad URL name passed to `url()` | Verify URL name; consider a safe wrapper |
| `csrf_input` missing | Middleware not active or not in context | Ensure `CsrfViewMiddleware` is in `MIDDLEWARE` |
