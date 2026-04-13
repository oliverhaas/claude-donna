---
name: tests-screenshot
description: Visual regression testing with Playwright screenshots. Use when adding screenshot tests, updating baselines, setting up the assert_screenshot fixture, or configuring the CI visual workflow.
user-invocable: false
---

# Screenshot / Visual Regression Tests

Pixel-level comparison of UI state against baseline images using Playwright. Screenshot tests run separately from the main test suite and have their own CI workflow.

## Test Pattern

```python
@pytest.mark.screenshot
def test_combobox_default(combobox_page, assert_screenshot):
    """Visual snapshot: ComboBox in default (empty) state."""
    wrapper = combobox_page.locator(".dropdown.combobox").first
    assert_screenshot(wrapper, "combobox-default.png")

@pytest.mark.screenshot
def test_combobox_open_dropdown(combobox_page, assert_screenshot):
    """Visual snapshot: ComboBox with dropdown open."""
    inp = combobox_page.locator('input[name="language_single"]')
    inp.click()
    inp.fill("P")
    combobox_page.wait_for_timeout(150)
    wrapper = combobox_page.locator(".dropdown.combobox").first
    assert_screenshot(wrapper, "combobox-open.png", capture_dropdown=True)
```

Every screenshot test:
1. Marks with `@pytest.mark.screenshot`
2. Uses a page fixture that navigates to the right URL
3. Interacts with the page to reach the desired state
4. Calls `assert_screenshot(locator, "filename.png")` to capture and compare

## `assert_screenshot` Fixture

```python
# tests/widgets/conftest.py
import numpy as np
from pathlib import Path
from PIL import Image

_SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
_PER_PIXEL_TOLERANCE = 10  # per-channel tolerance out of 255

@pytest.fixture
def assert_screenshot(request):
    update_mode = request.config.getoption("--update-screenshots", default=False)

    def _assert(
        locator,
        name: str,
        *,
        threshold: float = 0.002,
        padding: int = 8,
        capture_dropdown: bool = False,
    ):
        _SCREENSHOTS_DIR.mkdir(exist_ok=True)
        baseline_path = _SCREENSHOTS_DIR / name

        # Disable animations and hide cursor for deterministic captures
        locator.page.add_style_tag(
            content="*, *::before, *::after { transition: none !important; animation: none !important; }"
        )

        if capture_dropdown:
            # Make absolute-positioned dropdowns flow normally for capture
            locator.evaluate("el => el.style.position = 'static'")

        screenshot = locator.screenshot(
            animations="disabled",
            caret="hide",
        )

        actual = Image.open(io.BytesIO(screenshot))
        if padding > 0:
            actual = _add_padding(actual, padding)

        if update_mode:
            actual.save(baseline_path)
            return

        if not baseline_path.exists():
            actual.save(baseline_path)
            pytest.skip(f"Baseline created: {name}")

        baseline = Image.open(baseline_path)
        diff_ratio = _compare_images(actual, baseline)

        if diff_ratio > threshold:
            # Save debug artifacts
            results_dir = Path("test-results")
            results_dir.mkdir(exist_ok=True)
            stem = name.rsplit(".", 1)[0]
            actual.save(results_dir / f"{stem}-actual.png")
            baseline.save(results_dir / f"{stem}-baseline.png")
            _save_diff_image(actual, baseline, results_dir / f"{stem}-diff.png")

            pytest.fail(
                f"Screenshot {name}: {diff_ratio:.4%} pixels differ (threshold: {threshold:.4%})"
            )

    return _assert


def _compare_images(actual: Image.Image, baseline: Image.Image) -> float:
    """Return fraction of pixels that differ beyond per-channel tolerance."""
    # Pad to same size if dimensions differ
    max_w = max(actual.width, baseline.width)
    max_h = max(actual.height, baseline.height)
    actual = _pad_to_size(actual, max_w, max_h)
    baseline = _pad_to_size(baseline, max_w, max_h)

    a = np.array(actual.convert("RGBA"), dtype=np.int16)
    b = np.array(baseline.convert("RGBA"), dtype=np.int16)
    diff = np.abs(a - b)
    different = np.any(diff > _PER_PIXEL_TOLERANCE, axis=2)
    return different.sum() / different.size


def _save_diff_image(actual: Image.Image, baseline: Image.Image, path: Path):
    """Create a diff image highlighting changed pixels in red."""
    max_w = max(actual.width, baseline.width)
    max_h = max(actual.height, baseline.height)
    actual = _pad_to_size(actual, max_w, max_h)
    baseline = _pad_to_size(baseline, max_w, max_h)

    a = np.array(actual.convert("RGBA"), dtype=np.int16)
    b = np.array(baseline.convert("RGBA"), dtype=np.int16)
    diff = np.abs(a - b)
    mask = np.any(diff > _PER_PIXEL_TOLERANCE, axis=2)

    result = np.array(baseline.convert("RGBA"))
    result[mask] = [255, 0, 0, 255]
    Image.fromarray(result).save(path)
```

### Capture options

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `threshold` | `0.002` | Max fraction of differing pixels (0.2%) |
| `padding` | `8` | Pixels of padding around captured element |
| `capture_dropdown` | `False` | Set `position: static` to capture absolute-positioned overflow |

## Directory Structure

```
tests/widgets/
├── conftest.py                    # assert_screenshot fixture, page fixtures
├── screenshots/                   # Baseline images (committed to git)
│   ├── combobox-default.png
│   ├── combobox-open.png
│   ├── toggle-checked.png
│   └── ...
├── test_combobox.py               # Screenshot tests per widget
├── test_toggle.py
└── test_rating.py
```

Baselines live in `screenshots/` next to the test files and are committed to git.

## pytest Configuration

```toml
[tool.pytest.ini_options]
markers = [
    "screenshot: visual regression tests with Playwright snapshots",
]
```

```python
# conftest.py (root)
def pytest_addoption(parser):
    parser.addoption(
        "--update-screenshots",
        action="store_true",
        default=False,
        help="Regenerate screenshot baselines instead of comparing.",
    )
```

Main CI excludes screenshot tests:

```bash
uv run pytest tests/ -m "not screenshot" -n auto
```

## CI Workflow (`.github/workflows/visual.yml`)

Separate workflow from main CI. Three triggers:

### Scheduled + manual (baseline regeneration)

Runs weekly (e.g. Monday 6am UTC) and on `workflow_dispatch`:

```yaml
on:
  schedule:
    - cron: "0 6 * * 1"
  workflow_dispatch:

jobs:
  update-baselines:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - # ... setup Python, uv, Playwright ...
      - run: uv run pytest tests/widgets/ -m screenshot --update-screenshots --no-cov -q
      - name: Check for changes
        id: diff
        run: |
          if git diff --quiet tests/widgets/screenshots/; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"
          fi
      - name: Create baseline PR
        if: steps.diff.outputs.changed == 'true'
        run: |
          git checkout -B chore/update-screenshot-baselines
          git add tests/widgets/screenshots/
          git commit -m "chore: update screenshot baselines [auto]"
          git push --force origin chore/update-screenshot-baselines
          gh pr create --title "chore: update screenshot baselines" \
            --body "Auto-generated by visual regression workflow." \
            --base main || true
```

### Pull request (comparison)

```yaml
on:
  pull_request:

jobs:
  visual-check:
    runs-on: ubuntu-latest
    steps:
      - # ... setup ...
      - run: uv run pytest tests/widgets/ -m screenshot --no-cov -q
      - name: Upload failure artifacts
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: screenshot-diffs
          path: test-results/
          retention-days: 14
      - name: Create baseline update PR on failure
        if: failure()
        run: |
          uv run pytest tests/widgets/ -m screenshot --update-screenshots --no-cov -q
          BRANCH="chore/update-screenshots-${GITHUB_HEAD_REF}"
          git checkout -B "$BRANCH"
          git add tests/widgets/screenshots/
          git commit -m "chore: update screenshot baselines for ${GITHUB_HEAD_REF} [auto]"
          git push --force origin "$BRANCH"
          gh pr create --title "chore: update baselines for ${GITHUB_HEAD_REF}" \
            --base "${GITHUB_HEAD_REF}" \
            --body "Screenshot baselines changed. Review diffs in artifact." || true
```

On failure: uploads diff artifacts AND creates a PR targeting the source branch with updated baselines.

## Updating Baselines

**Locally:**
```bash
uv run pytest tests/widgets/ -m screenshot --update-screenshots
```

**Via CI:** merge the auto-generated baseline PR, or trigger the workflow manually.

**For intentional changes:**
1. Make the code change
2. Run screenshot tests -- they fail
3. Check `test-results/` diff images to verify the change is correct
4. Run with `--update-screenshots` to regenerate
5. Commit baselines alongside code changes

## Deterministic Captures

The fixture disables sources of non-determinism:
- `animations="disabled"` on Playwright screenshot call
- `caret="hide"` removes blinking cursor
- CSS injection: `transition: none !important; animation: none !important;`
- `time-machine` for time-dependent content (freeze time in the test)

Use `page.wait_for_timeout(150)` after interactions that trigger CSS transitions to ensure the final state is captured.

## Dependencies

| Package | Purpose |
|---------|---------|
| pytest-playwright | Browser automation |
| Pillow | Image loading and manipulation |
| numpy | Pixel-level array comparison |
