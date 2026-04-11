---
name: django-permissions
description: Permission patterns for Django: auth backends, object-level permissions, view enforcement, admin integration. Use when implementing access control, custom permission logic, or role-based authorization.
user-invocable: false
---

# Django Permissions

## Overview

Django's permission system has two levels:
- **Model-level**: does the user have the `app.action_model` permission at all?
- **Object-level**: does the user have permission on *this specific instance*?

Built-in permissions cover model-level only. Object-level requires a custom backend or django-guardian.

---

## Model-Level Permissions

### Built-in Codenames

Django auto-creates `add`, `change`, `delete`, `view` for every model:

```python
user.has_perm('articles.add_article')
user.has_perm('articles.change_article')
user.has_perm('articles.delete_article')
user.has_perm('articles.view_article')
```

### Custom Permissions

Define in `Meta.permissions`:

```python
class Article(models.Model):
    class Meta:
        permissions = [
            ('publish_article', 'Can publish articles'),
            ('feature_article', 'Can feature articles on the homepage'),
        ]
```

Codename becomes `articles.publish_article`. Generate with `makemigrations`.

---

## Custom Auth Backends

Write a backend when permission logic depends on business rules, not just database rows.

```python
# app_name/backends.py

class ArticlePermissionBackend:
    """Custom backend: authors can edit their own drafts."""

    def authenticate(self, request, **kwargs):
        return None  # Not an auth backend, skip authentication

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False
        if perm == 'articles.change_article' and obj is not None:
            return obj.author == user_obj and obj.status == 'draft'
        return False
```

Register in settings:

```python
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'articles.backends.ArticlePermissionBackend',
]
```

`user.has_perm()` queries backends in order and returns `True` on first positive result. `ModelBackend` checks database permissions and superuser status. Add custom backends after it.

### Backend Rules

- Return `False` (not `None`) when denying — `None` means "abstain", which lets subsequent backends decide.
- Always check `user_obj.is_active` first.
- Backends are called even when `obj` is `None` (model-level check); guard with `if obj is not None`.
- Keep each backend focused on one domain.

---

## Object-Level Permissions with django-guardian

Use django-guardian when you need persistent, assignable object permissions stored in the database.

```bash
pip install django-guardian
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    'guardian',
]
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
]
ANONYMOUS_USER_NAME = None  # Disable anonymous user if not needed
```

```python
from guardian.shortcuts import assign_perm, remove_perm, get_users_with_perms

# Grant permission
assign_perm('articles.change_article', user, article)

# Revoke permission
remove_perm('articles.change_article', user, article)

# Check
user.has_perm('articles.change_article', article)  # True

# Grant to group
assign_perm('articles.change_article', group, article)

# List users with a given permission on an object
editors = get_users_with_perms(article, only_with_perms_in=['change_article'])
```

### guardian QuerySet Filtering

```python
from guardian.shortcuts import get_objects_for_user

# All articles this user can change
articles = get_objects_for_user(user, 'articles.change_article', Article)
```

---

## Permission Checking in Views

### Function-Based Views

```python
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied

@login_required
def article_edit(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if not request.user.has_perm('articles.change_article', article):
        raise PermissionDenied
    ...

# Model-level shortcut (redirects to login or raises 403)
@permission_required('articles.publish_article', raise_exception=True)
def article_publish(request, pk):
    ...
```

### Class-Based Views

```python
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin

class ArticleUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Article
    permission_required = 'articles.change_article'
    raise_exception = True  # Raise 403 instead of redirect for authenticated users

    def has_permission(self):
        # Override for object-level: called after login check
        obj = self.get_object()
        return self.request.user.has_perm('articles.change_article', obj)
```

### Manual Check Pattern (preferred for object-level)

For object-level checks in CBVs, override `dispatch` or `get_object`:

```python
class ArticleUpdateView(LoginRequiredMixin, UpdateView):
    model = Article

    def dispatch(self, request, *args, **kwargs):
        article = get_object_or_404(Article, pk=kwargs['pk'])
        if not request.user.has_perm('articles.change_article', article):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
```

Do not call `get_object()` in `dispatch` if it triggers extra queries — fetch directly via `get_object_or_404`.

### HTMX / Partial Responses

Same rules apply. Raise `PermissionDenied`; Django returns 403. Handle it in the HTMX error handler on the client side.

---

## Permission Checking in Templates

```html
{% if perms.articles.publish_article %}
    <a href="{% url 'article_publish' article.pk %}">Publish</a>
{% endif %}

{% if perms.articles.change_article %}
    <a href="{% url 'article_edit' article.pk %}">Edit</a>
{% endif %}
```

`perms` is available in templates when `django.contrib.auth.context_processors.auth` is in `TEMPLATES[...]['OPTIONS']['context_processors']` (it is by default).

Object-level checks are not available via `perms` in templates. Pass a boolean from the view instead:

```python
# view
def article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk)
    can_edit = request.user.has_perm('articles.change_article', article)
    return render(request, 'articles/detail.html', {'article': article, 'can_edit': can_edit})
```

```html
{% if can_edit %}
    <a href="{% url 'article_edit' article.pk %}">Edit</a>
{% endif %}
```

---

## Custom Permission Classes (DRF / Django Ninja)

### Django REST Framework

```python
from rest_framework.permissions import BasePermission

class IsArticleAuthor(BasePermission):
    """Object-level: only the author can edit."""

    message = 'You are not the author of this article.'

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return obj.author == request.user
```

```python
class ArticleViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsArticleAuthor]
```

### Django Ninja

Django Ninja does not have a dedicated permission class system. Use `request.user.has_perm()` directly in the endpoint or factor into a helper:

```python
def require_perm(perm: str, obj=None):
    """Dependency-style helper for Ninja endpoints."""
    def check(request):
        if not request.user.has_perm(perm, obj):
            raise HttpError(403, 'Permission denied')
    return check

@router.post('/articles/{pk}/publish')
def publish_article(request, pk: int):
    article = get_object_or_404(Article, pk=pk)
    if not request.user.has_perm('articles.publish_article', article):
        raise HttpError(403, 'Permission denied')
    ...
```

---

## Group and Role Patterns

### Simple Group-Based Roles

```python
# Assign users to groups
from django.contrib.auth.models import Group

editors = Group.objects.get(name='editors')
user.groups.add(editors)

# Check via has_perm (groups inherit their permissions)
user.has_perm('articles.publish_article')  # True if editors group has this perm
```

### Setting Up Groups Programmatically

Use a data migration or a management command — not `post_migrate` signals for production data:

```python
# management/commands/setup_roles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

class Command(BaseCommand):
    help = 'Create default permission groups'

    def handle(self, *args, **options):
        editors, _ = Group.objects.get_or_create(name='editors')
        publish_perm = Permission.objects.get(codename='publish_article')
        editors.permissions.add(publish_perm)
        self.stdout.write('Roles configured.')
```

### Role Field on User Profile

For finer-grained roles that don't map 1:1 to permissions, add a role field and check it in a backend:

```python
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=[('viewer', 'Viewer'), ('editor', 'Editor'), ('admin', 'Admin')],
        default='viewer',
    )

class RolePermissionBackend:
    def authenticate(self, request, **kwargs):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False
        try:
            profile = user_obj.userprofile
        except UserProfile.DoesNotExist:
            return False
        if profile.role == 'admin':
            return True
        if profile.role == 'editor' and perm.startswith('articles.'):
            return True
        return False
```

---

## Django Admin Integration

### ModelAdmin Permission Methods

Override `has_*_permission` on `ModelAdmin` to control admin access:

```python
class ArticleAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        if obj is None:
            return super().has_change_permission(request)
        # Only author or superuser can edit
        return obj.author == request.user or request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(author=request.user)
```

### Restricting Admin Access to Groups

```python
class ArticleAdmin(admin.ModelAdmin):
    def has_module_perms(self, request, app_label):
        return request.user.groups.filter(name='editors').exists()
```

---

## Testing Permission Logic

Use `pytest-django` with `UserFactory` and `rf` (RequestFactory) or `client`.

```python
import pytest
from django.test import RequestFactory
from articles.models import Article

@pytest.mark.django_db
def test_author_can_edit_own_draft(rf):
    author = UserFactory.create()
    other = UserFactory.create()
    article = ArticleFactory.create(author=author, status='draft')

    assert author.has_perm('articles.change_article', article)
    assert not other.has_perm('articles.change_article', article)


@pytest.mark.django_db
def test_publish_requires_permission(client):
    user = UserFactory.create()
    article = ArticleFactory.create(status='draft')
    client.force_login(user)

    response = client.post(f'/articles/{article.pk}/publish/')
    assert response.status_code == 403


@pytest.mark.django_db
def test_editor_group_can_publish():
    from django.contrib.auth.models import Group, Permission
    editor = UserFactory.create()
    group = Group.objects.create(name='editors')
    perm = Permission.objects.get(codename='publish_article')
    group.permissions.add(perm)
    editor.groups.add(group)

    # Flush permission cache (Django caches per-request on the user object)
    editor = editor.__class__.objects.get(pk=editor.pk)

    assert editor.has_perm('articles.publish_article')


@pytest.mark.django_db
def test_inactive_user_denied():
    user = UserFactory.create(is_active=False)
    article = ArticleFactory.create()
    assert not user.has_perm('articles.change_article', article)
```

### Permission Cache

Django caches permissions on the user object after the first `has_perm` call. In tests, re-fetch the user from the database after modifying groups or permissions:

```python
user = User.objects.get(pk=user.pk)  # Clears the _perm_cache
```

Or use `user._perm_cache.clear()` and `user._user_perm_cache.clear()` directly.

---

## Checklist

- Model-level permissions defined in `Meta.permissions` or using built-in codenames.
- Custom backends registered in `AUTHENTICATION_BACKENDS` (after `ModelBackend`).
- Backends return `False` to deny, `None`/`False` to abstain — never `True` for unrecognized perms.
- Object-level checks done in view, not template.
- Template shows actions only when the view has passed a `can_*` boolean.
- Groups set up via management command or data migration, not in application code.
- Permission cache cleared in tests after modifying user groups/perms.
