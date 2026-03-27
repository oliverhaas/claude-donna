---
name: tests-view
description: View test guidelines: verify rendering, input handling, and expected behaviors. Use when writing tests for Django views or endpoints.
user-invocable: false
---
# View Testing Guidelines

View tests should verify that views render correctly, handle input properly, and implement expected behaviors.

## Core Test Cases

Authentication/authorization tests
```python
def test_view_redirects_to_login_if_not_logged_in(client, product):
    url = reverse("products:detail", kwargs={"pk": product.pk})
    response = client.get(url)
    assert response.status_code == 302
    assert "/accounts/sign-in" in response.headers["location"]
```

URL/route tests
```python
def test_view_url_exists_at_desired_location(client, user):
    client.force_login(user)
    response = client.get("/path/to/view/")
    assert response.status_code == 200

def test_view_url_accessible_by_name(client, user, product):
    client.force_login(user)
    response = client.get(reverse("products:detail", kwargs={"pk": product.pk}))
    assert response.status_code == 200
```

Template tests
```python
def test_view_uses_correct_template(client, user, product):
    client.force_login(user)
    response = client.get(reverse("products:detail", kwargs={"pk": product.pk}))
    assert response.status_code == 200
    assert any(t.name == "expected_template.html" for t in response.templates)
```

Context tests
```python
def test_context_contains_expected_data(client, user, product):
    client.force_login(user)
    response = client.get(reverse("products:detail", kwargs={"pk": product.pk}))
    assert response.status_code == 200
    assert "expected_key" in response.context
    assert len(response.context["list_items"]) == 5
```

## Form Handling Tests

For views that process forms:

```python
def test_form_submission_valid_data(client, user):
    client.force_login(user)
    form_data = {
        "field1": "value1",
        "field2": "value2",
    }
    response = client.post(reverse("products:create"), form_data)

    # Check for expected response (redirect or 200)
    assert response.status_code == 200

    # Check that data was saved correctly
    assert b"Success message" in response.content

def test_form_submission_invalid_data(client, user):
    client.force_login(user)
    form_data = {
        "field1": "",  # Required field left empty
        "field2": "value2",
    }
    response = client.post(reverse("products:create"), form_data)

    # Check that form errors are displayed
    assert response.status_code == 200
    assert "field1" in response.context["form"].errors
```

## Testing Content

Check that expected content exists in the response:

```python
def test_page_contains_expected_elements(client, user, product):
    client.force_login(user)
    response = client.get(reverse("products:detail", kwargs={"pk": product.pk}))

    assert response.status_code == 200
    assert b"Expected text" in response.content

    # For more complex HTML parsing
    soup = BeautifulSoup(response.content, "html.parser")
    assert soup.find(id="expected_element_id") is not None
```

Do not check for too specific content, e.g. the exact and complete text a paragraph would show, because the exact text might change. Rather check for just the html elements existing or the most important keyword in a textblock at most.

## HTMX Testing

For views using HTMX:

```python
def test_htmx_partial_request(client, user, product):
    client.force_login(user)
    response = client.get(
        reverse("products:detail", kwargs={"pk": product.pk}),
        headers={
            "HX-Request": "true",
            "HX-Target": "partial_id",
        }
    )

    assert response.status_code == 200
    # Verify the response contains only the partial, not the full page
    assert b"<html" not in response.content
```



---
