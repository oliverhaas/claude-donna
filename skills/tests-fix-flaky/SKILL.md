---
name: tests-fix-flaky
description: Investigate and fix a flaky test to make it reliable.
disable-model-invocation: true
---

# Fix Flaky Test

Investigate and fix a flaky test to make it reliable.

## 0. Which Test?

Which flaky test do you want me to investigate?

Please provide the test path (e.g., `path/to/test.py::TestClass::test_method`).

## 1. Reproduce

```bash
# Run test multiple times - aim for at least 5 failures
uv run pytest --flake-finder --flake-runs=100 path/to/test.py::TestClass::test_method

# If flake rate is very low (1-2 failures in 100 runs), increase iterations
uv run pytest --flake-finder --flake-runs=500 path/to/test.py::TestClass::test_method
```

You need at least 5 failures to be confident the test is reproducibly flaky. With only 1-2 failures in 100 runs, run more iterations (500+) to gather enough failure data.

## 2. Common Root Causes

### Unit / Integration Tests

- **Inconsistent factory data**: `Iterator()` and randomization are fine, but the generated combinations must be valid and make domain sense (e.g. VAT ID must match the country). When a test depends on a specific field value, set it explicitly rather than relying on what the factory happens to generate
- **Ordering dependencies**: Use `set()` comparison for collection membership, not `list()` — QuerySet order is undefined. Never patch production code (e.g. adding `.order_by()`) just to make a test deterministic — rewrite the test instead
- **Test isolation**: Usually use function-scoped fixtures or `setup_method`, not session-, module-, or class-scoped fixtures
- **Async tasks**: Mock `.delay()` calls to avoid background interference
- **Unique violations**: Use `factory.Sequence()` for unique fields in factories
- **on_commit callbacks**: Use `django_capture_on_commit_callbacks` fixture instead of `@pytest.mark.django_db(transaction=True)` (except e2e tests, they usually need `transaction=True`) — transaction mode truncates tables between tests causing FK constraint failures when callbacks fire late
- **Shared state**: Use `@pytest.fixture` with proper scope instead of modifying settings directly
- **Cache pollution**: Clear cache in fixtures or use `django_cache` fixture
- **External dependencies**: Never rely on external services (even google.com) — create local test servers or mocks
- **Time-dependent content**: Freeze time with `time-machine` for screenshot or date-dependent tests instead of masking individual elements

### E2E / Playwright

- **HTMX synchronization**: Wrap HTMX interactions with `page.expect_response()` to wait for POST responses before proceeding — concurrent unwaited requests cause data overwrites. This should improve after the frontend refactor
- **Navigation too fast**: Use `expect(locator).to_be_attached()` or `to_be_visible()` before interacting
- **Preline dropdowns**: Need custom interaction (click button, select via `data-value`), not native `select_option()`
- **Avoid `networkidle`**: Don't use `page.wait_for_load_state("networkidle")` — use specific `expect()` assertions on element state instead
- **HTMX swaps**: Use CSS selectors that reflect expected state `input[value='New Value']`, or `.to_have_attribute("value", "New Title")`
- **E2E assertions**: Test user-facing behavior, not internal state — e2e tests shouldn't break when internals change. Use PK/ID-based element selectors, not text content selectors
- **Test data setup**: Use factory parameters to prevent unwanted object creation (e.g. `factory_param__relation=[]`) instead of manual `.delete()` cleanup

## 3. Fix & Verify

```bash
# Apply fix, then verify with at least the same number of runs you used to reproduce
uv run pytest --flake-finder --flake-runs=100 path/to/test.py::test_method

# If you needed 500 runs to get 5+ failures, verify with 500+ runs
uv run pytest --flake-finder --flake-runs=500 path/to/test.py::test_method
```

Use at least the same number of runs you used when reproducing. If it took 500 runs to see 5 failures, you need 500+ consecutive passes to be confident the fix works.

## 4. Remove xfail Decorator

Only remove `@pytest.mark.xfail(reason="flaky")` if all of these are true:

1. You reproduced at least 5 failures with flakefinder
2. You implemented a fix for the root cause
3. You verified at least N consecutive passes (where N = number of runs used to reproduce)

If any condition isn't met, keep the xfail decorator.

## 5. Commit & Open PR

Create a branch, commit the fix, push, and open a PR:

```bash
# Create branch with descriptive name
git checkout -b chore/fix-flaky-test-name

# Commit with conventional commit format
git add -A && git commit -m "chore: fix flaky test test_name"

# Push and create PR (no description needed for simple fixes)
git push --set-upstream origin chore/fix-flaky-test-name
gh pr create --title "chore: fix flaky test test_name" --body ""
```


---
