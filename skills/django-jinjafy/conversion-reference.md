# DTL to Jinja2 Conversion Reference

Complete mapping of every Django Template Language construct to its Jinja2 equivalent.

## Tag Conversions

### Loading

```
DTL:    {% load i18n static admin_list %}
Jinja2: (removed -- extensions/globals are registered in the environment)
```

### Translation

```
DTL:    {% translate 'Home' %}
Jinja2: {{ gettext('Home') }}

DTL:    {% trans "Home" %}
Jinja2: {{ gettext("Home") }}

DTL:    {% blocktranslate with name=app.name %}Models in {{ name }}{% endblocktranslate %}
Jinja2: {% trans name=app.name %}Models in {{ name }}{% endtrans %}

DTL:    {% blocktranslate count counter=items|length %}One item{% plural %}{{ counter }} items{% endblocktranslate %}
Jinja2: {% trans count=items|length %}One item{% pluralize %}{{ count }} items{% endtrans %}
        (note: Jinja2 uses `count` not `counter` in the plural block)

DTL:    {% blocktranslate trimmed %}...{% endblocktranslate %}
Jinja2: {% trans %}...{% endtrans %}
        (Jinja2 trans blocks trim whitespace by default)

DTL:    {% blocktranslate trimmed context "some context" %}...{% endblocktranslate %}
Jinja2: {% trans context "some context" %}...{% endtrans %}
```

### URLs

```
DTL:    {% url 'admin:index' %}
Jinja2: {{ url('admin:index') }}

DTL:    {% url 'admin:app_list' app_label=cl.opts.app_label %}
Jinja2: {{ url('admin:app_list', app_label=cl.opts.app_label) }}

DTL:    {% url 'admin:password_change' as password_url %}
Jinja2: {% set password_url = url('admin:password_change', silent=True) %}
        (silent=True catches NoReverseMatch and returns "")

DTL:    {% url opts|admin_urlname:'changelist' %}
Jinja2: {{ url(opts|admin_urlname('changelist')) }}
```

### Static Files

```
DTL:    {% static "admin/css/base.css" %}
Jinja2: {{ static('admin/css/base.css') }}
```

### CSRF

```
DTL:    {% csrf_token %}
Jinja2: {{ csrf_input }}
        (injected by Django's Jinja2 backend automatically)
```

### Template Inheritance

```
DTL:    {% extends "admin/base.html" %}
Jinja2: {% extends "admin/base.html" %}  (same)

DTL:    {% block content %}...{% endblock %}
Jinja2: {% block content %}...{% endblock %}  (same)

DTL:    {{ block.super }}
Jinja2: {{ super() }}
```

### Includes

```
DTL:    {% include "admin/app_list.html" %}
Jinja2: {% include "admin/app_list.html" %}  (same)

DTL:    {% include "admin/app_list.html" with show_changelinks=True %}
Jinja2: {% set show_changelinks = True %}
        {% include "admin/app_list.html" %}
        (Jinja2 include passes full context; set variables before include)

DTL:    {% include "admin/app_list.html" with show_changelinks=True only %}
Jinja2: {% set show_changelinks = True %}
        {% include "admin/app_list.html" %}
        (no direct equivalent for `only`; variables leak into parent scope)
```

### Control Flow

```
DTL:    {% for item in items %}...{% empty %}Nothing{% endfor %}
Jinja2: {% for item in items %}...{% else %}Nothing{% endfor %}

DTL:    {% if x %}...{% elif y %}...{% else %}...{% endif %}
Jinja2: {% if x %}...{% elif y %}...{% else %}...{% endif %}  (same)

DTL:    {% with name=value %}...{% endwith %}
Jinja2: {% set name = value %}
        (no block scoping -- variable persists in current scope)
```

### Loop Variables

```
DTL:    {{ forloop.counter }}     -> Jinja2: {{ loop.index }}      (1-based)
DTL:    {{ forloop.counter0 }}    -> Jinja2: {{ loop.index0 }}     (0-based)
DTL:    {{ forloop.last }}        -> Jinja2: {{ loop.last }}
DTL:    {{ forloop.first }}       -> Jinja2: {{ loop.first }}
DTL:    {{ forloop.revcounter }}  -> Jinja2: {{ loop.revindex }}
DTL:    {{ forloop.revcounter0 }} -> Jinja2: {{ loop.revindex0 }}
```

### Other Tags

```
DTL:    {% now "Z" %}
Jinja2: {{ now("Z") }}
        (custom global wrapping django.utils.dateformat.format)

DTL:    {% firstof user.get_short_name user.get_username %}
Jinja2: {{ user.get_short_name() or user.get_username() }}
        (note: must call methods with ())

DTL:    {% cycle 'row1' 'row2' %}
Jinja2: {{ loop.cycle('row1', 'row2') }}
        (only works inside a for loop)

DTL:    {% spaceless %}...{% endspaceless %}
Jinja2: (remove tag; use {%- -%} trim markers for tight whitespace)

DTL:    {% filter capfirst %}{{ value }}{% endfilter %}
Jinja2: {{ value|capfirst }}

DTL:    {% get_current_language as LANGUAGE_CODE %}
Jinja2: {% set LANGUAGE_CODE = get_current_language() %}

DTL:    {% get_current_language_bidi as LANGUAGE_BIDI %}
Jinja2: {% set LANGUAGE_BIDI = get_current_language_bidi() %}

DTL:    {% autoescape off %}...{% endautoescape %}
Jinja2: {% autoescape false %}...{% endautoescape %}
```

## Filter Conversions

DTL filters use `:` for arguments; Jinja2 uses function call syntax `()`.

```
DTL:    {{ value|default:"fallback" }}
Jinja2: {{ value|default("fallback") }}

DTL:    {{ value|default_if_none:"fallback" }}
Jinja2: {{ value if value is not none else "fallback" }}

DTL:    {{ value|yesno:"Yes,No,Maybe" }}
Jinja2: {{ value|yesno("Yes,No,Maybe") }}  (custom filter)

DTL:    {{ value|capfirst }}
Jinja2: {{ value|capfirst }}  (custom filter wrapping django.utils.text.capfirst)

DTL:    {{ value|truncatewords:10 }}
Jinja2: {{ value|truncatewords(10) }}  (custom filter)

DTL:    {{ value|date:"DATE_FORMAT" }}
Jinja2: {{ value|date("DATE_FORMAT") }}  (custom filter)

DTL:    {{ value|length }}
Jinja2: {{ value|length }}  (same)

DTL:    {{ value|length_is:"1" }}
Jinja2: {{ value|length == 1 }}

DTL:    {{ value|stringformat:"s" }}
Jinja2: {{ value|string }}

DTL:    {{ value|urlencode }}
Jinja2: {{ value|urlencode_path }}  (custom filter)

DTL:    {{ value|unordered_list }}
Jinja2: {{ value|unordered_list }}  (custom filter)

DTL:    {{ value|safe }}
Jinja2: {{ value|safe }}  (same)

DTL:    {{ opts|admin_urlname:'changelist' }}
Jinja2: {{ opts|admin_urlname('changelist') }}
        (filter takes argument via function call syntax)

DTL:    {{ value|admin_urlquote }}
Jinja2: {{ value|admin_urlquote }}  (same, custom filter)

DTL:    {{ inline_admin_form|cell_count }}
Jinja2: {{ inline_admin_form|cell_count }}  (custom filter)

DTL:    {{ value|unlocalize }}
Jinja2: {{ value|unlocalize }}  (custom filter)
```

## Inclusion Tags (Admin)

The hardest conversion. Django admin uses `InclusionAdminNode` -- tags that call a Python function, get a dict, then render a sub-template with that dict as context.

### Pattern

```
DTL:    {% load admin_list %}
        {% result_list cl %}

Jinja2: {% set _ctx = result_list(cl) %}
        {% set result_hidden_fields_list = _ctx.result_hidden_fields %}
        {% set num_sorted_fields = _ctx.num_sorted_fields %}
        {% set results_list = _ctx.results %}
        {% set headers = _ctx.headers %}
        {% include "admin/change_list_results.html" %}
```

### All Inclusion Tags

| DTL Tag | Jinja2 Global | Sub-template |
|---------|---------------|--------------|
| `{% result_list cl %}` | `result_list(cl)` | `change_list_results.html` |
| `{% pagination cl %}` | `pagination(cl)` | `pagination.html` |
| `{% search_form cl %}` | `search_form(cl)` | `search_form.html` |
| `{% date_hierarchy cl %}` | `date_hierarchy(cl)` | `date_hierarchy.html` |
| `{% admin_actions %}` | `admin_actions(context)` | `actions.html` |
| `{% change_list_object_tools %}` | (inline in template) | `change_list_object_tools.html` |
| `{% submit_row %}` | `submit_row(context)` | `submit_line.html` |
| `{% prepopulated_fields_js %}` | `prepopulated_fields_js(context)` | `prepopulated_fields_js.html` |
| `{% change_form_object_tools %}` | (inline in template) | `change_form_object_tools.html` |

### Template Override Hierarchy

DTL's `InclusionAdminNode` resolves templates via 3-level lookup:

```
admin/{app_label}/{model_name}/{template_name}
admin/{app_label}/{template_name}
admin/{template_name}
```

In Jinja2, use a `select_admin_template()` helper with `{% include %}`:

```jinja2
{% include select_admin_template(opts, "change_list_results.html") %}
```

Jinja2's `{% include %}` accepts a list and uses the first template found.

### Simple Tags as Global Functions

```
DTL:    {% paginator_number cl i %}
Jinja2: {{ paginator_number(cl, i) }}

DTL:    {% admin_list_filter cl spec %}
Jinja2: {{ admin_list_filter(cl, spec) }}

DTL:    {% add_preserved_filters url %}
Jinja2: {{ add_preserved_filters(url) }}
```

### Admin Log Tag

```
DTL:    {% load log %}
        {% get_admin_log 10 as admin_log for_user user %}

Jinja2: {% set admin_log = get_admin_log(10, user) %}
```

## Critical Gotchas

### 1. DTL Auto-Calls Methods; Jinja2 Does Not

The single biggest source of bugs. In DTL, `{{ obj.method }}` automatically calls `method()` if it's callable. In Jinja2, it renders the bound method object as a string like `<bound method Foo.bar of ...>`.

**Every method reference in DTL templates must have `()` added in Jinja2.**

Common offenders in Django admin:

```
{{ field.label_tag }}          -> {{ field.label_tag() }}
{{ field.errors }}             -> {{ field.errors() }}
{{ field.contents }}           -> {{ field.contents() }}
{{ line.errors }}              -> {{ line.errors() }}
{{ form.non_field_errors }}    -> {{ form.non_field_errors() }}
{{ formset.non_form_errors }}  -> {{ formset.non_form_errors() }}
{{ obj.pk_field.field }}       -> {{ obj.pk_field().field }}
{{ obj.fk_field.field }}       -> {{ obj.fk_field().field }}
{{ obj.deletion_field.field }} -> {{ obj.deletion_field().field }}
{{ field.field.errors.as_ul }} -> {{ field.field.errors.as_ul() }}
{{ form.errors.items }}        -> {{ form.errors.items() }}
```

Properties do NOT need `()` -- only methods. The tricky part is knowing which is which. Django admin helper classes (`AdminField`, `AdminReadonlyField`, `Fieldline`, `InlineAdminForm`) use methods where you'd expect properties.

### 2. Django's mark_safe() Is Not Recognized by Jinja2

Django's `SafeString` (from `mark_safe()`) does NOT have `__html__()`, which Jinja2 uses to detect pre-escaped HTML. Without a fix, all `mark_safe()` output gets double-escaped.

**Fix:** Patch `SafeData.__html__` in the Jinja2 environment factory:

```python
from django.utils.safestring import SafeData
if not hasattr(SafeData, "__html__"):
    SafeData.__html__ = str
```

### 3. Filters That Strip Safety

Django's `capfirst()` returns a plain `str` even when given a `SafeString`. This means `{{ value|capfirst }}` escapes HTML that was previously safe.

**Fix:** Wrap filters to preserve `Markup` status:

```python
def capfirst_safe(value):
    result = capfirst(str(value)) if value else ""
    if hasattr(value, "__html__"):
        return Markup(result)
    return result
```

### 4. Functions That Return Rendered HTML

Django's `admin_list_filter(cl, spec)` uses `get_template().render()` internally, returning a plain `str` of HTML (not `SafeString`). Jinja2 escapes it.

**Fix:** Wrap such functions to return `Markup`:

```python
def admin_list_filter_safe(cl, spec):
    return Markup(raw_admin_list_filter(cl, spec))
```

### 5. Context-Aware Tags Need @jinja2.pass_context

Django's `takes_context=True` tags become `@jinja2.pass_context`. Jinja2's `Context` object is immutable -- functions that mutate context crash with `TypeError`.

**Fix:** Always convert to `dict` first:

```python
@jinja2.pass_context
def submit_row_jinja2(context):
    ctx = dict(context)
    return raw_submit_row(ctx)
```

### 6. loop Variable Not Available in {% include %}

Jinja2 does NOT pass the `loop` variable from a `{% for %}` block into `{% include %}`d templates. DTL's `forloop` is part of the context and passes through.

**Fix:** Set needed values as regular variables before the include:

```jinja2
{% for item in items %}
    {% set is_last = loop.last %}
    {% include "child.html" %}
{% endfor %}
```

### 7. Block Names Cannot Contain Hyphens

DTL allows `{% block nav-sidebar %}`; Jinja2 does not -- block names must be valid Python identifiers.

**Fix:** Replace hyphens with underscores:

```
{% block nav-sidebar %}    -> {% block nav_sidebar %}
{% block object-tools %}   -> {% block object_tools %}
{% block dark-mode-vars %} -> {% block dark_mode_vars %}
```
