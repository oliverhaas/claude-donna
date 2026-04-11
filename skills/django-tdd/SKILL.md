---
name: django-tdd
description: TDD patterns for Django. Use when implementing any Django feature or bugfix test-first, or when structuring a red-green-refactor cycle.
user-invocable: false
---

# Django TDD Guidelines

Test-first on the Django stack. Write a failing test, write the minimum code to pass it, then refactor. See `tests-general` for organization conventions and `django-factories` for factory patterns.

## Red-Green-Refactor Cycle

1. **Red**: Write the smallest test that describes the desired behavior. Run it; confirm it fails.
2. **Green**: Write the minimum code that makes it pass. No extras.
3. **Refactor**: Clean up implementation and tests without changing behavior. Re-run to confirm green.

Never write implementation before there is a failing test for it.

## pytest-django Setup

```toml
# pyproject.toml
[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "config.settings.test"
addopts = "--reuse-db"
markers = [
    "unit: fast, isolated unit tests",
    "integration: tests with DB or external state",
    "e2e: browser-level end-to-end tests",
]
```

```python
# conftest.py (project root)
import pytest

@pytest.fixture(autouse=True)
def reset_sequences(db):
    """Optional: reset DB sequences for predictable PKs."""
    pass
```

## DB Access Markers

Use the narrowest marker needed:

```python
@pytest.mark.django_db          # basic read/write, wraps in transaction and rolls back
@pytest.mark.django_db(transaction=True)  # needed for signals that use on_commit, LISTEN/NOTIFY
```

Never use `TestCase` or `TransactionTestCase` — prefer `@pytest.mark.django_db(transaction=True)` when transaction-level behavior is required.

Access `db` or `django_db_setup` fixtures explicitly in fixtures; let the test's marker propagate it.

```python
@pytest.fixture
def product(db):
    return ProductFactory.create()

def test_product_is_active(product):  # db access granted via fixture
    assert product.is_active is True
```

## conftest Organization

```
project/
  conftest.py                 # shared fixtures: authenticated_client, mailoutbox wrappers
  app_name/
    tests/
      conftest.py             # app-scoped fixtures
      test_models.py
      test_views.py
      test_services.py
      test_forms.py
```

One `test_<layer>.py` per layer per app. Within each file, group related tests with a comment block — no test classes.

## Factory-Driven Test Data

Use `factory_boy` for all test data. See `django-factories` skill for factory patterns.

```python
# Minimal: let defaults handle everything not under test
def test_order_total_calculation(db):
    order = OrderFactory.create(items_count=3, item_price=Decimal("10.00"))
    assert order.total == Decimal("30.00")

# Override only what the test cares about
def test_inactive_user_cannot_login(client, db):
    user = UserFactory.create(is_active=False)
    response = client.post(reverse("login"), {"username": user.username, "password": "pass"})
    assert response.status_code == 200  # form re-render, not redirect
```

Never use `Model.objects.create(...)` directly in tests. Always use factories.

## Testing Models

Test model methods, properties, and `clean()` directly — no HTTP layer needed.

```python
@pytest.mark.unit
def test_article_slug_generated_on_save(db):
    article = ArticleFactory.create(title="Hello World", slug="")
    article.save()
    assert article.slug == "hello-world"

@pytest.mark.unit
def test_article_clean_raises_on_future_publish_date(db):
    article = ArticleFactory.build(published_at=timezone.now() + timedelta(days=1))
    with pytest.raises(ValidationError, match="published_at"):
        article.clean()

@pytest.mark.unit
def test_order_str_includes_reference(db):
    order = OrderFactory.create(reference="ORD-001")
    assert "ORD-001" in str(order)
```

Use `Factory.build()` (no DB hit) when testing logic that doesn't need persistence.

## Testing Views

See `tests-view` skill for the full view testing reference. TDD flow for a new view:

```python
# 1. Red: test the URL resolves before writing the view
def test_product_detail_url_resolves(db):
    url = reverse("products:detail", kwargs={"pk": 1})
    assert url == "/products/1/"

# 2. Red: test expected response before writing the view logic
def test_product_detail_returns_200(client, db):
    product = ProductFactory.create()
    client.force_login(UserFactory.create())
    response = client.get(reverse("products:detail", kwargs={"pk": product.pk}))
    assert response.status_code == 200

# 3. Red: test context data before populating it
def test_product_detail_context_has_product(client, db):
    product = ProductFactory.create()
    client.force_login(UserFactory.create())
    response = client.get(reverse("products:detail", kwargs={"pk": product.pk}))
    assert response.context["product"] == product
```

## Testing Services

Services are plain functions/static methods — test them directly, no HTTP overhead.

```python
@pytest.mark.django_db
def test_order_service_creates_order(db):
    user = UserFactory.create()
    product = ProductFactory.create(price=Decimal("9.99"))

    order = OrderService.order_create(user=user, product=product, quantity=2)

    assert order.pk is not None
    assert order.total == Decimal("19.98")
    assert order.user == user

@pytest.mark.django_db
def test_order_service_raises_on_out_of_stock(db):
    product = ProductFactory.create(stock=0)
    with pytest.raises(ValidationError, match="out of stock"):
        OrderService.order_create(user=UserFactory.create(), product=product, quantity=1)
```

Test the happy path first; add error/edge-case tests in the same file.

## Testing Forms

```python
@pytest.mark.unit
def test_signup_form_valid_with_required_fields():
    data = {"email": "user@example.com", "password1": "str0ng!", "password2": "str0ng!"}
    form = SignupForm(data=data)
    assert form.is_valid()

@pytest.mark.unit
def test_signup_form_invalid_on_duplicate_email(db):
    UserFactory.create(email="existing@example.com")
    data = {"email": "existing@example.com", "password1": "str0ng!", "password2": "str0ng!"}
    form = SignupForm(data=data)
    assert not form.is_valid()
    assert "email" in form.errors
```

## Testing Management Commands

```python
from django.core.management import call_command

@pytest.mark.django_db
def test_import_products_command_creates_records(tmp_path, db):
    csv_file = tmp_path / "products.csv"
    csv_file.write_text("name,price\nWidget,9.99\n")

    call_command("import_products", str(csv_file))

    assert Product.objects.filter(name="Widget").exists()

@pytest.mark.django_db
def test_import_products_command_skips_duplicates(tmp_path, db):
    ProductFactory.create(name="Widget")
    csv_file = tmp_path / "products.csv"
    csv_file.write_text("name,price\nWidget,9.99\n")

    call_command("import_products", str(csv_file))

    assert Product.objects.filter(name="Widget").count() == 1
```

## Mocking External Services

Mock at the integration boundary — the function that makes the outbound call, not the internal wrappers.

```python
def test_send_order_confirmation_calls_email_api(mocker, db):
    mock_send = mocker.patch("orders.emails.send_transactional_email")
    order = OrderFactory.create()

    send_order_confirmation(order)

    mock_send.assert_called_once()
    call_kwargs = mock_send.call_args.kwargs
    assert call_kwargs["to"] == order.user.email

def test_payment_service_raises_on_gateway_error(mocker, db):
    mocker.patch(
        "payments.gateway.charge",
        side_effect=GatewayError("card declined"),
    )
    with pytest.raises(PaymentError, match="card declined"):
        PaymentService.charge(order=OrderFactory.create(), amount=Decimal("9.99"))
```

Patch the name as it is imported in the module under test, not where it is defined.

## Database Access Patterns

```python
# Use refresh_from_db() to verify persistence, not in-memory state
def test_service_updates_status(db):
    order = OrderFactory.create(status="pending")
    OrderService.mark_complete(order=order)
    order.refresh_from_db()
    assert order.status == "complete"

# Soft delete: assert persisted field, not Python object state
def test_soft_delete_marks_record_inactive(db):
    product = ProductFactory.create(is_active=True)
    product.soft_delete()
    product.refresh_from_db()
    assert product.is_active is False

# on_commit hooks require transaction=True
@pytest.mark.django_db(transaction=True)
def test_post_save_signal_fires_on_commit(mocker):
    mock_notify = mocker.patch("orders.signals.notify_warehouse")
    OrderFactory.create(status="confirmed")
    mock_notify.assert_called_once()
```

## Performance Testing Patterns

Use pytest-django's `django_assert_num_queries` to pin query counts in hot paths.

```python
def test_order_list_view_query_count(client, django_assert_num_queries, db):
    user = UserFactory.create()
    OrderFactory.create_batch(10, user=user)
    client.force_login(user)

    with django_assert_num_queries(3):  # session + user + orders
        response = client.get(reverse("orders:list"))

    assert response.status_code == 200
```

Pin query counts after confirming N+1s are resolved — it acts as a regression guard. Re-evaluate the count if the view intentionally adds queries later.

---
