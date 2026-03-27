---
name: tests-playwright-e2e
description: End-to-end testing with pytest-playwright and live_server fixture. Use when writing browser-based E2E or integration tests.
user-invocable: false
---
# Playwright E2E Testing Guidelines

When writing e2e tests use pytest-playwright with the pytest-django `live_server` fixture.

## Test Structure

```python
import pytest
from django.urls import reverse
from playwright.sync_api import Page, expect

from accounts.tests.factories import PASSWORD_PLAINTEXT, UserFactory


def sign_in(page: Page, live_server, user) -> None:
    """Sign in helper for playwright tests."""
    page.goto(f"{live_server.url}{reverse('account_login')}")
    page.locator("[name=login]").fill(user.email)
    page.locator("[name=password]").fill(PASSWORD_PLAINTEXT)
    page.locator("button[type=submit]").click()
    page.wait_for_load_state("networkidle")
    expect(page).to_have_url(f"{live_server.url}/dashboard/")


@pytest.fixture
def user():
    return UserFactory.create()


@pytest.mark.django_db
def test_example(page: Page, live_server, user) -> None:
    sign_in(page, live_server, user)
    page.goto(f"{live_server.url}{reverse('my_view')}")

    # Use expect() for assertions with auto-waiting
    expect(page.locator("#my_element")).to_be_attached()
```

## Key Patterns

1. **Use `expect()` for assertions** - includes auto-waiting for elements:
   ```python
   expect(page.locator("#element")).to_be_attached()
   expect(page.locator("#element")).to_be_visible()
   expect(page.locator("#element")).to_have_text("expected")
   expect(page.locator("input")).to_have_value("expected")
   expect(page.locator("input")).to_be_disabled()
   ```

2. **Wait for HTML state after HTMX updates** - `expect()` auto-waits for HTML changes. For inputs: `to_have_value()` checks JS property (immediate), `to_have_attribute("value", ...)` checks HTML attribute (server state).
   ```python
   element.fill("New Title")
   page.locator("h1").click()  # Blur triggers HTMX save
   expect(element).to_have_attribute("value", "New Title")  # HTML attr = server state
   expect(page.locator("#status")).to_have_text("Saved")    # Or wait for other HTML changes
   ```

3. **Use specific selectors** - Playwright's strict mode errors when multiple elements match. Don't circumvent it with `.first`/`.nth()` - fix the selector instead. Strict mode makes tests much more reliable long-term.
   ```python
   page.locator("#main_heading").click()
   page.locator("#submit-button").click()
   page.locator("#form_section h1").click()
   ```

4. **Use `input_value()` for form values** - not `get_attribute("value")`:
   ```python
   current_value = page.locator("input").input_value()
   ```

5. **Use `press("End")` before `type()`** - to append text to existing content:
   ```python
   input_field.click()
   input_field.press("End")
   input_field.type(" appended text")
   ```

6. **Use `expect()` to actually wait** - browser e2e tests are slow; use `expect()` assertions to reliably wait for state changes before proceeding:
   ```python
   expect(element).to_have_attribute("value", "saved")
   expect(page.locator("#modal")).to_be_visible()
   expect(page).to_have_url(expected_url)
   ```

## Anti-Patterns

- **No `time.sleep()`** - never use, always flaky
- **No `page.wait_for_timeout()`** - only as absolute last resort
- **No custom DB polling** - don't poll `model.refresh_from_db()` in a loop
- **No `to_have_value()` after HTMX** - use `to_have_attribute("value", ...)` instead (see above)

## Common Assertions

```python
# Element presence
expect(element).to_be_attached()      # In DOM
expect(element).to_be_visible()       # Visible to user
expect(element).not_to_be_attached()  # Not in DOM

# Content
expect(element).to_have_text("text")

# Input values - choose based on timing needs:
expect(element).to_have_value("value")              # JS property (immediate)
expect(element).to_have_attribute("value", "value") # HTML attribute (after HTMX swap)

# State
expect(element).to_be_disabled()
expect(element).to_be_enabled()
expect(element).to_be_checked()

# URL
expect(page).to_have_url("http://...")
```



---
