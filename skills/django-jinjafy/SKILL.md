---
name: django-jinjafy
description: Use when converting Django templates (DTL) to Jinja2. Covers tag/filter syntax conversion, auto-call gotchas, mark_safe interop, and inclusion tag migration.
user-invocable: true
argument-hint: "[template-directory or file]"
---

# Django Jinjafy

Convert Django Template Language (DTL) templates to Jinja2. Handles tag syntax, filter mapping, template inheritance, and the subtle gotchas that cause silent bugs (double-escaping, method auto-calls, context scoping).

Scope: **project templates** -- your own app templates. Not Django's built-in admin templates (that's django-adminx).

## Workflow

### Phase 1: Automated Bulk Conversion

Write and run a Python conversion script against the target templates. The script handles all mechanical conversions that are safe to automate.

**Step 1: Identify target files**

```python
"""Find all Django templates to convert."""
from pathlib import Path

template_dir = Path("<template-dir>")
templates = sorted(template_dir.rglob("*.html"))
print(f"Found {len(templates)} templates")
for t in templates:
    print(f"  {t.relative_to(template_dir)}")
```

**Step 2: Bulk convert**

Write a script using `re.sub` for each safe conversion. Apply all replacements in a single pass per file.

```python
"""Automated DTL-to-Jinja2 conversion for safe, mechanical patterns."""
import re
from pathlib import Path

REPLACEMENTS: list[tuple[str, str | Callable]] = [
    # --- Remove {% load %} tags ---
    (r'^\s*\{%\s*load\s+[^%]+%\}\s*\n', ''),

    # --- Translation tags ---
    # {% translate "..." %} / {% trans "..." %} -> {{ gettext("...") }}
    (r'\{%\s*trans(?:late)?\s+"([^"]+)"\s*%\}', r'{{ gettext("\1") }}'),
    (r"\{%\s*trans(?:late)?\s+'([^']+)'\s*%\}", r"{{ gettext('\1') }}"),
    # {% blocktranslate -> {% trans
    (r'\{%\s*blocktranslate(\s)', r'{% trans\1'),
    (r'\{%\s*endblocktranslate\s*%\}', r'{% endtrans %}'),
    # {% plural %} -> {% pluralize %}
    (r'\{%\s*plural\s*%\}', r'{% pluralize %}'),
    # Remove `trimmed` (Jinja2 trims by default)
    (r'\{%\s*trans\s+trimmed\s*%\}', r'{% trans %}'),
    (r'\{%\s*trans\s+trimmed\s', r'{% trans '),

    # --- URL tags (simple, no args) ---
    (r"\{%\s*url\s+'([^']+)'\s*%\}", r"{{ url('\1') }}"),
    (r'\{%\s*url\s+"([^"]+)"\s*%\}', r'{{ url("\1") }}'),

    # --- Static files ---
    (r'\{%\s*static\s+"([^"]+)"\s*%\}', r'{{ static("\1") }}'),
    (r"\{%\s*static\s+'([^']+)'\s*%\}", r"{{ static('\1') }}"),

    # --- CSRF ---
    (r'\{%\s*csrf_token\s*%\}', r'{{ csrf_input }}'),

    # --- Template inheritance ---
    (r'\{\{\s*block\.super\s*\}\}', r'{{ super() }}'),

    # --- Control flow ---
    (r'\{%\s*empty\s*%\}', r'{% else %}'),
    (r'\{%\s*autoescape\s+off\s*%\}', r'{% autoescape false %}'),

    # --- Loop variables (order matters: counter0 before counter) ---
    (r'forloop\.counter0', r'loop.index0'),
    (r'forloop\.counter', r'loop.index'),
    (r'forloop\.revcounter0', r'loop.revindex0'),
    (r'forloop\.revcounter', r'loop.revindex'),
    (r'forloop\.first', r'loop.first'),
    (r'forloop\.last', r'loop.last'),

    # --- Filters (colon arg syntax -> function call syntax) ---
    (r'\|default:"([^"]+)"', r'|default("\1")'),
    (r"\|default:'([^']+)'", r"|default('\1')"),
    (r'\|truncatewords:(\d+)', r'|truncatewords(\1)'),
    (r'\|date:"([^"]+)"', r'|date("\1")'),
    (r'\|yesno:"([^"]+)"', r'|yesno("\1")'),
    (r'\|stringformat:"s"', r'|string'),
    (r'\|length_is:"(\d+)"', r'|length == \1'),
]


def convert_file(path: Path) -> bool:
    """Apply all safe conversions to a single file. Returns True if changed."""
    original = path.read_text()
    content = original
    for pattern, replacement in REPLACEMENTS:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    if content != original:
        path.write_text(content)
        return True
    return False


template_dir = Path("<template-dir>")
for path in sorted(template_dir.rglob("*.html")):
    if convert_file(path):
        print(f"  converted: {path.relative_to(template_dir)}")
```

**Step 3: Verify automated changes**

Review the diff, confirm every change looks correct, then commit before moving on.

```bash
git diff <template-dir>
git add <template-dir> && git commit -m "chore: automated DTL-to-Jinja2 bulk conversion"
```

Search for remaining DTL patterns the script didn't catch:

```bash
grep -rn '{%\s*load\s' <template-dir>
grep -rn '{%\s*url\s' <template-dir>          # remaining urls have args (Phase 2)
grep -rn '{%\s*static\s' <template-dir>
grep -rn 'forloop\.' <template-dir>
grep -rn 'block\.super' <template-dir>
grep -rn '{%\s*csrf_token' <template-dir>
```

### Phase 2: Extract Manual Work

These patterns require context and judgment. Write a scanner that extracts them into a report.

```python
"""Scan converted templates for patterns that need manual conversion."""
import re
from pathlib import Path

MANUAL_PATTERNS = [
    ("url with args", r'\{%\s*url\s+["\'][^"\']+["\']\s+\S'),
    ("url as var", r'\{%\s*url\s+.*\s+as\s+'),
    ("with block", r'\{%\s*with\s'),
    ("endwith", r'\{%\s*endwith\s*%\}'),
    ("include with", r'\{%\s*include\s+.*\s+with\s'),
    ("firstof", r'\{%\s*firstof\s'),
    ("cycle", r'\{%\s*cycle\s'),
    ("spaceless", r'\{%\s*spaceless\s*%\}'),
    ("block with hyphen", r'\{%\s*block\s+\S*-\S*\s'),
    ("get_current_language", r'\{%\s*get_current_language'),
    ("now tag", r'\{%\s*now\s'),
    ("filter tag", r'\{%\s*filter\s'),
    ("default_if_none", r'\|default_if_none:'),
    ("inclusion tag", r'\{%\s*(result_list|pagination|search_form|date_hierarchy|admin_actions|submit_row|prepopulated_fields_js)\s'),
]

template_dir = Path("<template-dir>")
for path in sorted(template_dir.rglob("*.html")):
    content = path.read_text()
    for name, pattern in MANUAL_PATTERNS:
        for i, line in enumerate(content.splitlines(), 1):
            if re.search(pattern, line):
                print(f"  [{name}] {path.relative_to(template_dir)}:{i}")
                print(f"    {line.strip()}")
```

**For each finding, convert manually using these patterns:**

| DTL | Jinja2 |
|-----|--------|
| `{% url 'name' arg=val %}` | `{{ url('name', arg=val) }}` |
| `{% url 'name' as var %}` | `{% set var = url('name', silent=True) %}` |
| `{% with name=value %}...{% endwith %}` | `{% set name = value %}` (no block scoping) |
| `{% include "x.html" with foo=True %}` | `{% set foo = True %}{% include "x.html" %}` |
| `{% firstof a b %}` | `{{ a or b }}` (add `()` if methods) |
| `{% cycle 'a' 'b' %}` | `{{ loop.cycle('a', 'b') }}` (for loops only) |
| `{% spaceless %}...{% endspaceless %}` | Remove; use `{%- -%}` trim markers |
| `{% block nav-sidebar %}` | `{% block nav_sidebar %}` |

After converting all manual patterns, review and commit:

```bash
git diff <template-dir>
git add <template-dir> && git commit -m "chore: manual DTL-to-Jinja2 conversions"
```

### Phase 3: Method Auto-Call Audit

**This is where silent bugs hide.** DTL auto-calls methods; Jinja2 does not. `{{ obj.method }}` in DTL calls `method()`, but in Jinja2 it renders `<bound method ...>`.

Write a scanner to extract all dotted attribute accesses that might need `()`:

```python
"""Extract dotted attribute accesses that may need () added."""
import re
from pathlib import Path

ATTR_RE = re.compile(r'\{\{[^}]*?(\w+(?:\.\w+)+)[^}]*?\}\}')

template_dir = Path("<template-dir>")
attrs: set[str] = set()
for path in sorted(template_dir.rglob("*.html")):
    for match in ATTR_RE.finditer(path.read_text()):
        attrs.add(match.group(1))

print("Dotted accesses to check (method -> add '()', property -> leave as-is):")
for attr in sorted(attrs):
    print(f"  {attr}")
```

For each match, determine if the attribute is a method or property. When unsure, inspect the Python class:

```python
"""Check if an attribute is a method or property."""
import inspect

# Example: check BoundField.label_tag
from django.forms import BoundField
attr = getattr(BoundField, "label_tag")
print(f"label_tag: callable={callable(attr)}, type={type(attr)}")
```

Common Django methods that need `()` -- see @conversion-reference.md for the full list.

After adding all necessary `()` calls, review and commit:

```bash
git diff <template-dir>
git add <template-dir> && git commit -m "chore: add method call parens for Jinja2 auto-call"
```

### Phase 4: Safety and Escaping Audit

Check for double-escaping issues. These need fixes in **Python code**, not templates.

1. **`mark_safe()` interop** -- Django's `SafeString` lacks `__html__()` that Jinja2 checks. Patch once in your Jinja2 environment setup:
   ```python
   from django.utils.safestring import SafeData
   if not hasattr(SafeData, "__html__"):
       SafeData.__html__ = str
   ```

2. **Filters that strip safety** -- `capfirst()` and similar return plain `str` even for `SafeString` input. Wrap to preserve Markup status.

3. **Functions returning rendered HTML** -- functions using `get_template().render()` return plain `str`. Wrap to return `Markup`.

4. **Context-aware tags** -- DTL's `takes_context=True` becomes `@jinja2.pass_context`. Remember Jinja2's `Context` is immutable -- convert to `dict` first.

See @conversion-reference.md for detailed fixes and code.

After applying Python-side fixes, review and commit:

```bash
git diff
git add -A && git commit -m "chore: fix mark_safe/escaping interop for Jinja2"
```

### Phase 5: Verification

```bash
# Look for these symptoms in rendered output:
grep -r 'bound method' <output>     # missed auto-call
grep -r '&amp;' <output>            # double-escaping
grep -r '&lt;' <output>             # double-escaping
```

Test every converted template by loading it in the browser. Pay special attention to:
- Forms (method calls on BoundField)
- Admin pages (inclusion tags, context passing)
- Pages with `mark_safe()` content
- Translated strings

## Full Reference

See @conversion-reference.md for the complete DTL-to-Jinja2 mapping tables (tags, filters, inclusion tags, loop variables, gotchas).
