---
name: error-handling
description: Exception hierarchy design, catch/propagate decisions, and error response patterns. Use when writing error handling in Django views, APIs, or service layer code.
user-invocable: false
---

# Error Handling Guidelines

## Exception Hierarchy

Define a base exception per app or domain. All domain-specific exceptions inherit from it. This lets callers catch broadly (the base) or narrowly (a specific subclass).

```python
# accounts/exceptions.py
class AccountsError(Exception):
    """Base for all accounts-domain errors."""

class UserNotFoundError(AccountsError):
    pass

class InsufficientPermissionsError(AccountsError):
    pass

class DuplicateEmailError(AccountsError):
    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"Email already registered: {email}")
```

```python
# orders/exceptions.py
class OrdersError(Exception):
    """Base for all orders-domain errors."""

class OrderNotFoundError(OrdersError):
    pass

class OrderAlreadyCancelledError(OrdersError):
    pass

class PaymentFailedError(OrdersError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Payment failed: {reason}")
```

Rules:
- One `exceptions.py` per app (or per domain package if the app is large)
- Base exception name matches the app: `<AppName>Error`
- Attach relevant data as attributes, not only in the message string
- Never inherit from `ValueError`, `RuntimeError`, or other builtins — use your domain base

## When to Catch vs Propagate

**Catch** when you can handle the error meaningfully: recover, retry, translate to a user-facing message, or add context.

**Propagate** (let it bubble) when the caller is better positioned to decide what to do.

```python
# Service: catch to translate low-level errors into domain errors
@staticmethod
def user_create(*, email: str, password: str) -> "User":
    try:
        user = User.objects.create_user(email=email, password=password)
    except IntegrityError as exc:
        raise DuplicateEmailError(email=email) from exc
    return user

# View: catch domain errors to produce HTTP responses
def register_view(request):
    ...
    try:
        user = AccountsService.user_create(email=email, password=password)
    except DuplicateEmailError:
        form.add_error("email", "This email is already registered.")
        return render(request, "accounts/register.html", {"form": form})
    return redirect("dashboard")
```

```python
# Service: propagate — let the caller handle it
@staticmethod
def order_cancel(*, order: "Order", user: "User") -> None:
    if order.status == "cancelled":
        raise OrderAlreadyCancelledError()
    order.status = "cancelled"
    order.full_clean()
    order.save()
```

Rules:
- Services translate low-level exceptions (DB errors, HTTP errors) into domain exceptions
- Services propagate domain exceptions upward — they do not produce HTTP responses
- Views and API endpoints are the correct place to catch domain exceptions and return responses
- Never swallow an exception silently (no bare `except: pass`)

## Django's Built-in Exceptions

These are handled by Django's middleware and produce standard HTTP responses automatically. Raise them in views or service code when appropriate.

```python
from django.http import Http404
from django.core.exceptions import PermissionDenied, ValidationError

# Http404 → 404 response (also triggers 404.html template)
def article_detail(request, pk):
    article = get_object_or_404(Article, pk=pk)
    # or:
    try:
        article = Article.objects.get(pk=pk)
    except Article.DoesNotExist:
        raise Http404

# PermissionDenied → 403 response
def admin_view(request):
    if not request.user.is_staff:
        raise PermissionDenied

# ValidationError — raised by full_clean(), caught in forms automatically
# In a service context, let it propagate to the view/form layer
```

Do not catch `Http404` or `PermissionDenied` inside services. Raise them from views only, or raise your own domain exceptions from services and translate in the view.

**Django 6.0 additions:**

- `Model.NotUpdated` — raised by `Model.save()` when a forced update (`update_fields` with `force_update=True`) finds no matching rows. Catch this instead of the generic `DatabaseError` for forced-update failures.
- `django.core.mail.BadHeaderError` is deprecated in Django 6.0. Python's email library raises `ValueError` for headers with prohibited characters; catch `ValueError` instead.

## Error Responses in Views

Django views: use form errors for user-visible validation feedback.

```python
def order_create_view(request):
    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            try:
                order = OrdersService.order_create(
                    user=request.user,
                    product_id=form.cleaned_data["product_id"],
                    quantity=form.cleaned_data["quantity"],
                )
            except PaymentFailedError as exc:
                form.add_error(None, f"Payment declined: {exc.reason}")
            except OrdersError:
                form.add_error(None, "Could not place order. Please try again.")
            else:
                return redirect("order_detail", pk=order.pk)
    else:
        form = OrderForm()
    return render(request, "orders/create.html", {"form": form})
```

## Error Responses in APIs (Django Ninja)

Use `HttpError` for explicit status codes. Let Pydantic validation errors surface automatically (Ninja handles them as 422).

```python
from ninja.errors import HttpError
from django.core.exceptions import ValidationError

@router.post("/orders/", response=OrderResponse)
def create_order(request, data: CreateOrderRequest) -> OrderResponse:
    try:
        order = OrdersService.order_create(
            user=request.user,
            product_id=data.product_id,
            quantity=data.quantity,
        )
    except PaymentFailedError as exc:
        raise HttpError(402, exc.reason)
    except OrderNotFoundError:
        raise HttpError(404, "Order not found")
    except OrdersError as exc:
        raise HttpError(400, str(exc))
    return OrderResponse.from_orm(order)
```

For consistent error shapes across the API, configure a global exception handler:

```python
# app/api.py
from ninja import NinjaAPI
from orders.exceptions import OrdersError

api = NinjaAPI()

@api.exception_handler(OrdersError)
def orders_error_handler(request, exc):
    return api.create_response(request, {"detail": str(exc)}, status=400)
```

## Structured Error Reporting (Logging Integration)

See the `logging` skill for log levels and formatting rules. In error handling:

- Log at `ERROR` for unexpected failures; do not log expected domain errors (e.g., duplicate email) at error level
- Use `logger.exception()` to capture the traceback automatically
- Always re-raise or raise a new exception after logging — do not log and swallow

```python
import logging

logger = logging.getLogger(__name__)

@staticmethod
def payment_charge(*, order: "Order", amount: Decimal) -> None:
    try:
        payment_gateway.charge(order.id, amount)
    except payment_gateway.NetworkError as exc:
        logger.exception("Payment gateway network error for order %s", order.id)
        raise PaymentFailedError(reason="Gateway unreachable") from exc
    except payment_gateway.DeclinedError as exc:
        # Expected — no error log, just a domain exception
        raise PaymentFailedError(reason=str(exc)) from exc
```

Use `raise ... from exc` to chain exceptions so the original traceback is preserved.

## Service Layer Error Patterns

See the `django-services` skill for service structure. Error handling within services:

```python
@staticmethod
@transaction.atomic
def order_fulfil(*, order: "Order") -> None:
    if order.status != "paid":
        raise OrdersError(f"Cannot fulfil order in status '{order.status}'")

    try:
        InventoryService.reserve_stock(order=order)
    except InventoryError as exc:
        # Translate cross-domain error if needed, or let it propagate
        raise OrdersError("Stock reservation failed") from exc

    order.status = "fulfilling"
    order.full_clean()
    order.save()
```

Rules for services:
- Validate preconditions at the top of the method; raise immediately if not met
- Catch foreign-domain exceptions and re-raise as your domain's exception if the caller shouldn't need to know about the foreign domain
- Let `ValidationError` from `full_clean()` propagate — the caller (view/form) handles it
- Use `@transaction.atomic` — if an exception is raised mid-way, the transaction rolls back automatically

## Retry-Safe Error Handling

When a service operation may be retried (e.g., from a Celery task), it must be idempotent or use explicit guards.

```python
# orders/tasks.py
@shared_task(
    autoretry_for=(PaymentFailedError,),
    retry_backoff=True,
    max_retries=3,
)
def charge_order_task(*, order_id: int) -> None:
    order = Order.objects.get(pk=order_id)
    if order.status == "paid":
        return  # Already done — safe to retry
    OrdersService.payment_charge(order=order, amount=order.total)
```

For exceptions that should NOT be retried (e.g., user input errors, permanent failures), do not include them in `autoretry_for`:

```python
# Non-retryable: raise immediately, do not retry
class PermanentPaymentError(OrdersError):
    """Card permanently declined, fraud flagged, etc."""

@shared_task(
    autoretry_for=(PaymentFailedError,),  # Only transient errors
    max_retries=3,
)
def charge_order_task(*, order_id: int) -> None:
    ...
    # PermanentPaymentError bubbles out and is NOT retried
```

See the `celery-tasks` skill for task error patterns.

## Anti-Patterns

**Bare except** — catches `SystemExit`, `KeyboardInterrupt`, and hides bugs. Always name what you expect:
```python
try:
    process()
except SpecificError:
    handle()
```

**Swallowing errors** — never `except Exception: pass`. Log it even if you don't re-raise:
```python
try:
    send_email(user)
except Exception:
    logger.exception("Failed to send email to user %s", user.id)
```

**Exception-driven flow control** — use the API designed for the case, not a try/except:
```python
value = cache.get(key, default=None)
if value is None:
    value = compute_value()
```

**Catching too broadly** — catch only your domain exception, not `Exception`:
```python
try:
    result = OrdersService.order_create(...)
except OrdersError as exc:
    return HttpResponse(str(exc), status=400)
```

**Losing the original exception** — always use `raise ... from exc` when re-raising:
```python
try:
    db_call()
except IntegrityError as exc:
    raise DuplicateEmailError(email) from exc
```

## Modern Python Exception Features

### ExceptionGroup and `except*`

`ExceptionGroup` allows bundling multiple exceptions raised concurrently (e.g., from `asyncio.TaskGroup`). Use `except*` to match and handle sub-exceptions by type while letting others propagate.

```python
import asyncio

async def fetch_all(urls: list[str]) -> list[str]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch(url)) for url in urls]
    return [t.result() for t in tasks]
    # If any tasks raise, TaskGroup raises ExceptionGroup

# Handle specific sub-exception types:
try:
    results = await fetch_all(urls)
except* TimeoutError as eg:
    # eg.exceptions contains only the TimeoutErrors
    logger.warning("Timed out on %d URLs", len(eg.exceptions))
except* ValueError as eg:
    raise  # re-raise the group
```

Only use `ExceptionGroup` / `except*` when you are actually dealing with concurrent operations (e.g., `asyncio.TaskGroup`, manual grouping). Do not use it as a replacement for ordinary `except` clauses.
