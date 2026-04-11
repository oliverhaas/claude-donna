---
name: django-templates
description: Django template patterns for inheritance, includes, partials (Django 6.0), custom tags/filters, fragment caching, context processors, and HTMX partials. Use when writing or reviewing Django templates or template infrastructure.
user-invocable: false
---

# Django Templates

## Template Inheritance

Use a single base layout and extend it. Keep the inheritance chain shallow: `base.html` -> `app_base.html` -> page template is usually as deep as you need.

```html
{# templates/base.html #}
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{% block title %}My Site{% endblock %}</title>
  {% block extra_css %}{% endblock %}
</head>
<body>
  {% block header %}
    <header>{% include "partials/nav.html" %}</header>
  {% endblock %}

  <main>
    {% block content %}{% endblock %}
  </main>

  {% block extra_js %}{% endblock %}
</body>
</html>
```

```html
{# templates/blog/base.html #}
{% extends "base.html" %}

{% block content %}
  <div class="blog-layout">
    <div class="blog-main">{% block blog_content %}{% endblock %}</div>
    <aside>{% block sidebar %}{% endblock %}</aside>
  </div>
{% endblock %}
```

```html
{# templates/blog/post_detail.html #}
{% extends "blog/base.html" %}

{% block title %}{{ post.title }} – My Site{% endblock %}

{% block blog_content %}
  <article>
    <h1>{{ post.title }}</h1>
    {{ post.body }}
  </article>
{% endblock %}
```

**Block conventions:**
- `title` — page `<title>` content
- `content` — main body
- `extra_css` / `extra_js` — per-page static additions
- Call `{{ block.super }}` when you want to append, not replace, parent content

## Include vs. Component Patterns

`{% include %}` is a simple file insertion. Use it for reusable snippets that need access to the current context.

```html
{# Pass explicit context to isolate the include from surrounding variables #}
{% include "partials/card.html" with item=product only %}
```

`with ... only` prevents the included template from seeing the rest of the context. Prefer it for partials that should be self-contained.

For more complex reuse that needs its own logic, use a custom inclusion tag instead:

```python
# blog/templatetags/blog_tags.py
from django import template
from blog.models import Post

register = template.Library()

@register.inclusion_tag("partials/recent_posts.html")
def recent_posts(count=5):
    return {"posts": Post.objects.published().order_by("-created_at")[:count]}
```

```html
{# In any template #}
{% load blog_tags %}
{% recent_posts count=3 %}
```

Inclusion tags are the right choice when:
- The partial needs its own queryset
- The caller should not have to pass data
- The partial is used in multiple apps

## Custom Template Tags and Filters

### Filters

Filters transform a value. Keep them pure — no side effects, no database access.

```python
# myapp/templatetags/myapp_filters.py
from django import template
from django.utils.safestring import mark_safe
import bleach

register = template.Library()

@register.filter
def clamp(value, max_length):
    """Truncate value to max_length characters."""
    try:
        value = str(value)
        if len(value) <= max_length:
            return value
        return value[:max_length] + "…"
    except (TypeError, ValueError):
        return value

@register.filter(is_safe=True)
def sanitize(value):
    """Strip all HTML except allowed tags."""
    allowed = ["b", "i", "em", "strong", "a"]
    return mark_safe(bleach.clean(str(value), tags=allowed, strip=True))
```

Mark with `is_safe=True` only when your filter always returns safe HTML. Never call `mark_safe()` on user input without sanitizing first.

### Simple Tags

For tags that return a value but don't render a template:

```python
@register.simple_tag(takes_context=True)
def active_if(context, url_name):
    """Return 'active' if the current request matches url_name."""
    request = context["request"]
    from django.urls import reverse, NoReverseMatch
    try:
        return "active" if request.path == reverse(url_name) else ""
    except NoReverseMatch:
        return ""
```

```html
{% load myapp_filters %}
<a href="{% url 'home' %}" class="{% active_if 'home' %}">Home</a>
```

### Block Tags (assignment_tag / simple_tag with as)

```python
@register.simple_tag
def settings_value(name):
    from django.conf import settings
    return getattr(settings, name, "")
```

```html
{% settings_value "SITE_NAME" as site_name %}
<title>{{ site_name }}</title>
```

### Template Tag File Location

```
myapp/
└── templatetags/
    ├── __init__.py
    └── myapp_tags.py   # one file per app is usually enough
```

Always name the module after the app to avoid collisions. `{% load myapp_tags %}` in templates that use it.

## Template Partials (Django 6.0)

Django 6.0 introduced built-in template partials via `{% partialdef %}` and `{% partial %}` tags. Partials let you define a reusable named fragment inside a template and render it multiple times without a separate file.

### Defining and rendering partials

```html
{% load partials %}

{% partialdef product-card %}
  <div class="card">
    <h3>{{ product.name }}</h3>
    <p>{{ product.price }}</p>
  </div>
{% endpartialdef %}

{# Render the partial wherever needed in the same template #}
{% partial product-card %}
```

Use the `inline` option to render the partial immediately at the definition point and still make it available for later `{% partial %}` calls:

```html
{% partialdef product-card inline %}
  <div class="card">
    <h3>{{ product.name }}</h3>
    <p>{{ product.price }}</p>
  </div>
{% endpartialdef %}
```

The `inline` form is usually what you want: the partial renders in place on the full-page load, and HTMX re-renders it directly on subsequent requests.

### Accessing partials via template loading

Append `#partial_name` to the template path to render only that fragment. Works with `render()`, `get_template()`, and `{% include %}`:

```python
# views.py
def product_list(request):
    context = {"products": Product.objects.active()}
    if request.htmx:
        # Render only the fragment, not the full page
        return render(request, "shop/product_list.html#product-list-fragment", context)
    return render(request, "shop/product_list.html", context)
```

```html
{# shop/product_list.html #}
{% extends "base.html" %}
{% load partials %}

{% block content %}
  {% partialdef product-list-fragment inline %}
    <ul id="product-list">
      {% for product in products %}
        <li>{{ product.name }}</li>
      {% endfor %}
    </ul>
  {% endpartialdef %}
{% endblock %}
```

The `#partial_name` syntax also works with `{% include %}`:

```html
{% include "shop/product_list.html#product-list-fragment" %}
```

### When to use partials vs. include

- **`{% partialdef %}`** — the fragment lives inside the full-page template; no separate file needed; ideal for HTMX targets co-located with their surrounding page context.
- **`{% include %}`** — the fragment is genuinely shared across multiple unrelated templates and belongs in its own file.

**Migrating from `django-template-partials` (third-party):** Django 6.0's built-in partials are based on this package. A [migration guide](https://github.com/carltongibson/django-template-partials/blob/main/Migration.md) is available if you used it before upgrading.

## Template Fragment Caching

Cache expensive template fragments with `{% cache %}`. The cache key is built from the name plus any extra arguments.

```html
{% load cache %}

{# Cache for 600 seconds. Cache key includes user.pk so each user gets their own cached fragment. #}
{% cache 600 "sidebar" user.pk %}
  {% include "partials/sidebar.html" %}
{% endcache %}

{# Cache a public fragment indefinitely (0 = no expiry) #}
{% cache 0 "homepage_hero" %}
  {% include "partials/hero.html" %}
{% endcache %}
```

**Key arguments:**
- First positional: timeout in seconds (0 = no expiry)
- Second positional: fragment name (hardcoded string, not a variable)
- Remaining: vary-by values (user id, locale, etc.)

**Cache backend:** `{% cache %}` uses the `default` cache. To use a named backend, use the `using` argument:

```html
{% cache 300 "product_card" product.pk using "fragments" %}
  ...
{% endcache %}
```

**Invalidation:** The `{% cache %}` tag does not automatically invalidate. For programmatic invalidation, use `cache.delete()` with the same constructed key, or use a signal-driven approach:

```python
from django.core.cache import cache
from django.utils.cache import make_template_fragment_key

# Invalidate from Python code
key = make_template_fragment_key("sidebar", [user.pk])
cache.delete(key)
```

Do not cache fragments that contain CSRF tokens or vary on request state you are not passing as key arguments.

## Context Processors

Context processors add variables to every template context. Use them for data that is needed globally (current user, site config, feature flags).

```python
# myapp/context_processors.py

def site_settings(request):
    """Inject site-wide settings into every template context."""
    from django.conf import settings
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SUPPORT_EMAIL": settings.SUPPORT_EMAIL,
    }

def feature_flags(request):
    """Inject feature flags for conditional template rendering."""
    from myapp.flags import get_flags_for_request
    return {"flags": get_flags_for_request(request)}
```

Register in settings:

```python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Custom
                "myapp.context_processors.site_settings",
                "myapp.context_processors.feature_flags",
            ],
        },
    }
]
```

**Guidelines:**
- Keep context processors cheap. They run on every request.
- Never do expensive queries inside a context processor without caching.
- Accept `request` as the only argument — the signature is fixed.
- Return a dict. If the processor has nothing to add (e.g., inactive feature), return `{}`.

## Template Loading and Namespacing

### Recommended `TEMPLATES` settings

```python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],   # Project-level templates
        "APP_DIRS": True,                    # Also load from app/templates/
        "OPTIONS": {
            "context_processors": [...],
        },
    }
]
```

With `APP_DIRS: True`, Django looks for `<app>/templates/` in each installed app.

### Namespacing by convention

Avoid name collisions by mirroring the app name inside `templates/`:

```
myapp/
└── templates/
    └── myapp/
        ├── base.html
        ├── list.html
        └── detail.html
```

Reference as `"myapp/list.html"` everywhere. The outer `templates/` directory is on the loader path; the `myapp/` prefix is the namespace.

### Project-level overrides

Put templates in `templates/` at the project root to override app templates:

```
project/
├── templates/
│   └── registration/
│       └── login.html   # overrides django.contrib.auth's login template
├── myapp/
│   └── templates/
│       └── myapp/
│           └── list.html
```

`DIRS` entries take precedence over `APP_DIRS` results.

### Jinja2

If you use Jinja2 (see `django-jinjafy` skill for migration guidance), configure a second backend:

```python
TEMPLATES = [
    {"BACKEND": "django.template.backends.django.DjangoTemplates", ...},
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "DIRS": [BASE_DIR / "jinja2"],
        "APP_DIRS": True,   # loads from app/jinja2/
        "OPTIONS": {"environment": "myapp.jinja2.environment"},
    },
]
```

## Performance Considerations

**Avoid logic in templates.** Querysets, aggregations, and complex conditionals belong in views or services. Templates should only iterate and render — not compute.

**N+1 in templates.** Accessing a related object in a loop without `select_related` or `prefetch_related` fires one query per iteration.

```python
# View — prefetch before passing to template
posts = Post.objects.select_related("author").prefetch_related("tags").all()
```

```html
{# Safe: no extra queries per loop iteration #}
{% for post in posts %}
  {{ post.author.name }}
  {% for tag in post.tags.all %}{{ tag.name }}{% endfor %}
{% endfor %}
```

See the `django-orm-queries` skill for full N+1 guidance.

**Template caching.** The default template loader caches compiled templates in memory in production (`django.template.loaders.cached.Loader`). In development, `APP_DIRS: True` re-reads from disk on each request. For production, configure the cached loader explicitly:

```python
# settings/production.py
TEMPLATES[0]["OPTIONS"]["loaders"] = [
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    )
]
# Remove APP_DIRS when specifying loaders manually
```

**`{% spaceless %}` and whitespace.** Rarely worth the complexity. Minify at the CDN/nginx level instead.

**Inline conditionals.** Prefer `default` and `default_if_none` filters over `{% if %}` blocks for simple fallbacks:

```html
{{ user.display_name|default:user.username }}
```

## HTMX Partial Rendering

HTMX requests typically need a fragment, not a full page. The cleanest approach is to check for `HX-Request` and render only the partial.

### Pattern 1: Django 6.0 partials (preferred)

Use `{% partialdef %}` with the `#partial_name` template loading syntax. No separate files, no extra dependencies:

```python
# views.py
def product_list(request):
    context = {"products": Product.objects.active()}
    if request.htmx:
        return render(request, "shop/product_list.html#product-list-fragment", context)
    return render(request, "shop/product_list.html", context)
```

```html
{# shop/product_list.html #}
{% extends "base.html" %}
{% load partials %}

{% block content %}
  {% partialdef product-list-fragment inline %}
    <ul id="product-list">
      {% for product in products %}
        <li>{{ product.name }}</li>
      {% endfor %}
    </ul>
  {% endpartialdef %}
{% endblock %}
```

The `inline` option renders the partial in place for the full-page response. The HTMX response renders only the fragment via `#product-list-fragment`. Single file, no duplication.

> Requires `django-htmx` (adds `request.htmx`). Alternative: check `request.headers.get("HX-Request")`.

See the [Template Partials (Django 6.0)](#template-partials-django-60) section above for the full partial syntax.

### Pattern 2: Separate partial templates

For fragments shared across multiple templates, a separate file is still the right choice:

```python
# views.py
def product_list(request):
    products = Product.objects.active()
    template = "shop/partials/product_list.html" if request.htmx else "shop/product_list.html"
    return render(request, template, {"products": products})
```

```html
{# shop/product_list.html — full page #}
{% extends "base.html" %}
{% block content %}
  {% include "shop/partials/product_list.html" %}
{% endblock %}
```

```html
{# shop/partials/product_list.html — fragment only #}
<ul id="product-list">
  {% for product in products %}
    <li>{{ product.name }}</li>
  {% endfor %}
</ul>
```

The full page includes the partial via `{% include %}`. HTMX requests get the partial directly. No duplication.

### HTMX out-of-band updates

Use `hx-swap-oob` to update multiple parts of the page from a single response:

```html
{# partials/cart_button.html — rendered out-of-band #}
<button id="cart-btn" hx-swap-oob="true">
  Cart ({{ cart_count }})
</button>
```

```python
def add_to_cart(request, product_id):
    # ... add logic ...
    response = render(request, "shop/partials/cart_item.html", {"item": item})
    # Append out-of-band fragment
    oob = render_to_string("shop/partials/cart_button.html", {"cart_count": cart.count()}, request)
    response.content += oob.encode()
    return response
```

See the `alpine-htmx` skill for Alpine.js state preservation during HTMX swaps (morph, shared stores, event coordination).

Keep partials in a `partials/` subdirectory within each app's template namespace. Reference as `"shop/partials/product_list.html"`.
