---
name: django-modern-patterns
description: Modern Django patterns and avoiding deprecated approaches. Use when writing Django views, forms, URLs, or template code.
user-invocable: false
---
# Django Modern Patterns

When working with Django code, follow these guidelines to avoid deprecated patterns and use modern approaches:

## Middleware

**AVOID: MiddlewareMixin (legacy pattern)**
```python
from django.utils.deprecation import MiddlewareMixin

class MyMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Old pattern
        return response
```

**USE: Modern callable class pattern**
```python
from collections.abc import Callable
from django.http import HttpRequest, HttpResponse

class MyMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        # Modern pattern
        return response
```

**Alternative: Function-based middleware**
```python
def my_middleware(get_response):
    def middleware(request):
        response = get_response(request)
        return response
    return middleware
```

## Form Patterns

**AVOID: Legacy form field patterns**
- Use modern form field types and validation
- Prefer Django's built-in validators over custom regex patterns where possible

**USE: Modern form validation**
```python
from django import forms
from django.core.validators import EmailValidator

class MyForm(forms.Form):
    email = forms.EmailField(validators=[EmailValidator()])  # Modern
```

## Model Patterns

**AVOID: Deprecated model field options**
- Check Django release notes for deprecated field options
- Avoid using `null=True` on CharField/TextField (use blank=True instead)

**USE: Modern model patterns**
```python
from django.db import models

class MyModel(models.Model):
    name = models.CharField(max_length=100, blank=True)  # Not null=True
    created_at = models.DateTimeField(auto_now_add=True)
```

## URL Patterns

**AVOID: django.conf.urls (deprecated in Django 4.0)**
```python
from django.conf.urls import url  # Deprecated
```

**USE: django.urls**
```python
from django.urls import path, include  # Modern

urlpatterns = [
    path('api/', include('api.urls')),
]
```

## Settings Patterns

**AVOID: Deprecated settings**
- Check for deprecated Django settings in release notes
- Use modern database engine names
- Use modern middleware names

## Template Patterns

**AVOID: Legacy template tags**
- Use modern template tag syntax
- Prefer newer built-in template filters

## General Guidelines

1. **Use Django's Built-in Tools**: Prefer Django's built-in functionality over third-party alternatives when possible
2. **Follow Django's Style Guide**: Use Django's recommended patterns and conventions
3. **Type Hints**: Add proper type hints to all Django components (views, models, forms, middleware)
4. **Test Patterns**: Use modern Django testing patterns (see tests-* cursor rules)

## Common Deprecation Patterns to Watch For

- `django.utils.deprecation.MiddlewareMixin` → Modern middleware patterns
- `django.conf.urls` → `django.urls`
- `django.utils.translation.ugettext*` → `django.utils.translation.gettext*`
- Old-style class-based views → Modern CBV patterns
- Legacy template context processors → Modern context processors

## When to Update

- **Immediate**: If using truly deprecated features that will break in next Django version
- **Next Refactor**: If using legacy patterns that have modern alternatives
- **Gradual**: For large codebases, update patterns incrementally during normal development

Always test thoroughly when updating deprecated patterns, as behavior may have subtle differences.

## Automated Enforcement

**PREFERRED: Use Ruff for automated detection**

This project uses Ruff for linting with Django-specific rules (`DJ*`) that can automatically catch many deprecated patterns:

- `DJ001`: Avoid `null=True` on string fields (use `blank=True`)
- `DJ003`: Deprecated render function patterns
- `DJ006`: Avoid `exclude` in ModelForm (use `fields`)
- `DJ007`: Avoid `__all__` in ModelForm (use `fields`)
- `DJ008`: ModelForm best practices

**Check Current Violations**:
```bash
ruff check --select DJ --output-format=concise
```

Automated detection is preferred over manual code review for catching deprecated Django patterns.

---
