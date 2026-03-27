---
name: django-services
description: Service layer guidelines: business logic organization, naming, error handling. Use when writing or reviewing service functions or moving logic out of views/models.
user-invocable: false
---

# Django Services Guidelines

> **When to use services**: Services are for larger projects or cross-cutting operations that span multiple models or coordinate external systems. For simpler entity-centric logic that lives on a single model, prefer the fat model pattern instead (see `django-fat-models` skill).

Services are where business logic lives. They speak the domain language, access databases, interact with external systems, and coordinate between different parts of the application.

## Core Principles

1. **Domain-focused**: Services speak the specific business language of the software
2. **Stateless**: Services should be stateless, with classes just for organization
3. **Atomic**: Each service operation should be a complete business transaction
4. **UI/API agnostic**: Services use primitive types and Django models only - no Pydantic, Django forms, or similarly tailored
5. **Testable**: Services should be easily testable in isolation
6. **Type-safe**: All services must use proper type hints

## Integration with Validation Layers

Services are the **shared business logic layer** between UI and API paths. See the `django-validation` skill for the complete validation strategy.

**Validation Flow:**
- **API Path**: Pydantic → Service Function → Django Model (`full_clean()`)
- **UI Path**: Django Form → Service Function → Django Model (`full_clean()`)

Services receive **primitive types** (str, int, Decimal, etc.) and **Django model instances** only - never Pydantic models or Django forms.

## Service Implementation

### Class-Based Services (Only Pattern)

**ALL services must be implemented as classes** with static methods only:

```python
# app_name/services.py
from typing import TYPE_CHECKING
from django.db import transaction
from django.core.exceptions import ValidationError

if TYPE_CHECKING:
    from .models import Article, Author
    from accounts.models import User

class BlogService:
    """Service for blog-related business operations."""
    
    @staticmethod
    @transaction.atomic
    def article_create(
        *,
        title: str,
        content: str,
        author: "Author",
        user: "User"
    ) -> "Article":
        """Create a new article with validation and side effects."""
        from ..models import Article
        
        article = Article(
            title=title,
            content=content,
            author=author,
            status='draft'
        )
        article.full_clean()  # Always validate!
        article.save()
        
        # Side effects
        BlogService._send_notification_email(article, user)
        BlogService._log_activity(article, user)
        
        return article
    
    @staticmethod
    def comment_create(*, article: "Article", content: str, user: "User") -> "Comment":
        """Create a comment - shows multiple related operations in one service."""
        # Implementation here
        pass
    
    @staticmethod
    def comment_list(*, article: "Article", user: "User") -> list["Comment"]:
        """Get comments visible to user - shows data retrieval in services."""
        visible_comment_ids = comments_visible_for(user=user, article=article)
        return Comment.objects.filter(id__in=visible_comment_ids, article=article)
    
    @staticmethod
    def _send_notification_email(article: "Article", user: "User") -> None:
        """Private helper method - also static."""
        pass

# Usage: BlogService.article_create(title="My Article", ...)
# Usage: BlogService.comment_list(article=article, user=user)
```


## Service Organization

### File Structure

```
app_name/
├── services.py              # Simple services
├── services/
│   ├── __init__.py
│   ├── blog.py              # Blog-related services
│   └── users.py             # User-related services
```

**When to split**: Start with `services.py`. Split into sub-modules when you have many services or distinct sub-domains.

### Naming Convention

**Pattern**: `<OverarchingEntity>Service.<entity>_<action>()`

**Class Names**: Use overarching domain entity:
- `BlogService`, `UserService`, `LibraryService`

**Method Names**: Use specific `<entity>_<action>` within the overarching service:
- `BlogService.article_create()`, `BlogService.comment_create()`, `BlogService.tag_assign()`
- `UserService.user_create()`, `UserService.profile_update()`, `UserService.password_reset()`

Benefits:
- **Clear namespace**: `BlogService` groups all blog-related operations
- **IDE autocomplete**: Type `BlogService.` to see all available operations  
- **Entity clarity**: Method name shows exactly what entity and action
- **Logical grouping**: Related entities grouped under overarching domain

## Service Guidelines

### 1. Keyword-Only Arguments (Mandatory)

All service methods MUST start parameters with `*` to enforce keyword-only arguments:

```python
def article_create(*, title: str, author: Author) -> Article:  # Correct: has *
def article_create(title: str, author: Author) -> Article:     # Wrong: missing *
```

### 2. Key Implementation Rules

- **Type hints**: Always use `TYPE_CHECKING` imports and proper annotations
- **Validation**: Always call `model.full_clean()` before `model.save()`
- **Transactions**: Use `@transaction.atomic` for multi-step operations
- **Service composition**: Services can call other services to build complex operations
- **Async tasks**: Use `task.delay_on_commit(...)` for tasks after DB commit

## Integration Patterns

### API Endpoints (Thin Layer)

API endpoints extract primitive values from Pydantic models and pass them to services:

```python
# API endpoint - extract primitives from Pydantic, pass to service
@router.post("/articles/", response=ArticleResponse)
def create_article_api(
    request, 
    payload: CreateArticleRequest
) -> ArticleResponse:
    # Extract primitive types from Pydantic model
    article = BlogService.article_create(
        title=payload.title,                  # str
        content=payload.content,              # str
        author=request.user.author,           # Django model instance
        user=request.user                     # Django model instance
    )
    return ArticleResponse.model_validate(article)
```

### Django Views (Reuse Same Services)

Views extract cleaned data from forms and pass primitives to the same services:

```python
def article_create_view(request):
    if request.method == "POST":
        form = ArticleForm(request.POST)
        if form.is_valid():
            # Extract primitive types from form.cleaned_data
            article = BlogService.article_create(
                title=form.cleaned_data['title'],       # str
                content=form.cleaned_data['content'],   # str
                author=request.user.author,             # Django model instance
                user=request.user                       # Django model instance
            )
            return redirect('article_detail', pk=article.pk)
    else:
        form = ArticleForm()
    return render(request, 'articles/create.html', {'form': form})
```

**Key Point**: The exact same service method is called from both API and UI with the same parameter types. This ensures business logic consistency across all interfaces.

## Anti-Patterns to Avoid

- Service classes with instance state (`__init__` with attributes)
- Missing `*` for keyword-only arguments
- Passing Pydantic models or Django forms to services
- Services returning HTTP responses or API-specific objects
- Missing `full_clean()` validation or `@transaction.atomic`

## Testing Services

Test services like any other function - create test data with factories and call service methods directly.


## Summary

- **Use class-based services only** - no standalone functions
- **Use static methods only** - no instance state or `self` usage  
- **Use keyword-only arguments** (mandatory `*`) with type hints
- **Always validate** with `full_clean()`
- **Keep services UI/API agnostic** - use primitive types and Django models only
- **Never pass** Pydantic models or Django forms to services
- **Compose services** to build complex operations
- **Test thoroughly** with clear assertions
- **Follow naming convention**: `<OverarchingEntity>Service.<entity>_<action>()`
- **Reference django-validation skill** for complete validation strategy

---
