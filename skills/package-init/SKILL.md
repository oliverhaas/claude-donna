---
name: package-init
description: "Scaffold a new Python package with our standard tooling: hatchling, ruff, ty/mypy, pytest, GitHub Actions CI/CD, mkdocs, pre-commit."
user-invocable: true
argument-hint: "<package-name> [description]"
---

# Package Init

Scaffold a new Python package based on our standard project structure. Takes a package name and optional description, then sets up everything.

## Step 1: Gather Info

Parse `$ARGUMENTS` for:
- **Package name** (e.g. `django-foo`) - the pip-installable name
- **Module name** - derived from package name (e.g. `django_foo`)
- **Description** - from args or ask the user

Ask the user:
- Is this a Django package? (affects dependencies, classifiers, test settings)
- Initial Python version support? (default: `>=3.12`)
- Initial Django version support? (default: `>=5.2,<7` if Django package)
- Native extension? (Cython, PyO3/Rust, or none) — if yes, see "Native Extensions" at the bottom for overrides on top of the standard scaffold

## Step 2: Create GitHub Repository

```bash
gh repo create oliverhaas/{package-name} --public --license mit --clone
cd {package-name}
```

If the repo already exists, just clone it. If we're already in the right directory, skip this.

The default branch must be `main` (not `master`). If `gh repo create` initializes with `master`, rename it: `git branch -M main`.

## Step 3: Create Directory Structure

```
{package-name}/
├── {module_name}/
│   ├── __init__.py              # version and public API
│   └── py.typed                 # PEP 561 marker
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── settings/                # only for Django packages
│       ├── __init__.py
│       ├── base.py
│       └── urls.py
├── docs/
│   ├── index.md
│   ├── getting-started/
│   │   └── installation.md
│   └── reference/
│       └── changelog.md
├── .github/
│   ├── dependabot.yml
│   └── workflows/
│       ├── ci.yml
│       ├── publish.yml
│       ├── tag.yml
│       ├── docs.yml
│       └── dependabot-automerge.yml
├── .gitignore
├── .python-version
├── .pre-commit-config.yaml
├── pyproject.toml
├── mkdocs.yml
├── LICENSE
└── README.md
```

## Step 4: pyproject.toml

```toml
[project]
name = "{package-name}"
version = "0.1.0a1"
description = "{description}"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.12"
keywords = []
authors = [{ name = "Oliver Haas", email = "ohaas@e1plus.de" }]
classifiers = [
  "Development Status :: 2 - Pre-Alpha",
  "Intended Audience :: Developers",
  "License :: OSI Approved :: MIT License",
  "Operating System :: OS Independent",
  "Programming Language :: Python",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3 :: Only",
  "Programming Language :: Python :: 3.12",
  "Programming Language :: Python :: 3.13",
  "Programming Language :: Python :: 3.14",
  "Typing :: Typed",
  # Add "Framework :: Django" classifiers if Django package
]
dependencies = [
  # Add "Django>=5.2,<7" if Django package
]

[project.urls]
Homepage = "https://github.com/oliverhaas/{package-name}"
Documentation = "https://oliverhaas.github.io/{package-name}/"
Repository = "https://github.com/oliverhaas/{package-name}.git"
Changelog = "https://oliverhaas.github.io/{package-name}/reference/changelog/"

[dependency-groups]
dev = [
  "pre-commit==4.5.1",
  "pytest==9.0.2",
  "pytest-cov==7.1.0",
  "pytest-xdist==3.8.0",
  "ruff==0.15.8",
  # Non-Django: "ty==0.0.24"
  # Django: "mypy==1.19.1", "django-stubs==6.0.1", "pytest-django==4.12.0"
]
docs = ["mkdocs==1.6.1", "mkdocs-material==9.7.6", "mike==2.1.4"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["{module_name}"]

[tool.hatch.build.targets.sdist]
include = ["{module_name}", "LICENSE", "README.md"]

[tool.ruff]
target-version = "py313"
line-length = 120
fix = true

[tool.ruff.lint]
select = ["ALL"]
ignore = [
  "COM812",
  "D",
  "E501",
  "EM",
  "TRY003",
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = [
  "ANN", "ARG", "F841", "FBT", "PT006", "PT011",
  "PT013", "PT018", "S101", "S105",
]

# --- Type checker: use ONE of the following ---

# Non-Django packages: use ty
[tool.ty.environment]
python-version = "3.13"

[[tool.ty.overrides]]
include = ["tests/**"]
[tool.ty.overrides.rules]
unresolved-attribute = "ignore"

# Django packages: use mypy instead of ty
# [tool.mypy]
# python_version = "3.12"
# plugins = ["mypy_django_plugin.main"]
# pretty = true
# show_error_codes = true
# show_error_context = true
# warn_redundant_casts = true
# warn_unused_ignores = true
#
# [tool.django-stubs]
# django_settings_module = "tests.settings.base"

[tool.pytest.ini_options]
addopts = "--cov={module_name} --cov-report=term-missing --cov-report=xml --no-cov-on-fail"
testpaths = ["tests"]
xfail_strict = true
# Add DJANGO_SETTINGS_MODULE = "settings.base" if Django package
# Add pythonpath = ["tests"] if Django package

[tool.coverage.run]
omit = ["tests/*"]

[tool.coverage.report]
precision = 2
skip_covered = true
```

## Step 5: .pre-commit-config.yaml

```yaml
default_stages: [pre-commit]
default_install_hook_types:
  - pre-commit
  - pre-push
fail_fast: false

default_language_version:
  python: python3.13

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-ast
      - id: check-case-conflict
      - id: check-json
      - id: check-merge-conflict
      - id: check-symlinks
      - id: check-toml
      - id: check-yaml
      - id: debug-statements
      - id: detect-private-key
      - id: end-of-file-fixer
        stages: [pre-commit]
      - id: mixed-line-ending
        args: ["--fix=lf"]

  - repo: https://github.com/ComPWA/taplo-pre-commit
    rev: v0.9.3
    hooks:
      - id: taplo-format
        args: ["--", "--indent-string", "  ", "--reorder-arrays", "--reorder-keys"]

  - repo: https://github.com/asottile/add-trailing-comma
    rev: v3.1.0
    hooks:
      - id: add-trailing-comma

  - repo: local
    hooks:
      - id: uv-sync-check
        name: uv-sync-check
        language: system
        entry: uv sync
        pass_filenames: false

      - id: ruff-check
        name: ruff-check
        entry: uv run ruff check --fix
        language: system
        pass_filenames: false

      - id: ruff-format
        name: ruff-format
        entry: uv run ruff format
        language: system
        pass_filenames: false

  # --- Type checker hook: use ONE ---

  # Non-Django:
  - repo: local
    hooks:
      - id: ty
        name: ty
        language: system
        entry: uv run ty check {module_name}/
        pass_filenames: false
        always_run: true
        stages: [pre-push]

  # Django (replace ty block above with this):
  # - repo: local
  #   hooks:
  #     - id: mypy
  #       name: mypy
  #       language: system
  #       entry: uv run mypy {module_name}/
  #       pass_filenames: false
  #       always_run: true
  #       stages: [pre-push]
```

## Step 6: GitHub Actions

### .github/workflows/ci.yml

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v7
      - run: uv python install 3.14
      - run: uv sync --group dev
      - run: uv run ruff check
      - run: uv run ruff format --check
      # Non-Django:
      - run: uv run ty check {module_name}/
      # Django:
      # - run: uv run mypy {module_name}/

  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.12", "3.13", "3.14"]
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v7
      - run: uv python install ${{{{ matrix.python-version }}}}
      - run: uv sync --group dev
      - run: uv run pytest -n auto
      - name: Upload coverage
        if: matrix.python-version == '3.13'
        uses: codecov/codecov-action@v5
        with:
          files: ./coverage.xml
          fail_ci_if_error: false
```

### .github/workflows/publish.yml

```yaml
name: Publish to PyPI

on:
  push:
    tags: ["v*"]
  workflow_dispatch:
    inputs:
      version:
        description: "Version to publish (e.g., 1.0.0)"
        required: true

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          ref: ${{{{ github.event.inputs.version && format('v{{0}}', github.event.inputs.version) || github.ref }}}}
      - uses: astral-sh/setup-uv@v7
      - run: uv python install 3.12
      - run: uv sync --group dev
      - run: uv run ruff check
      - run: uv run ruff format --check
      - run: uv run pytest -n auto

  publish:
    needs: [test]
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/project/{package-name}/
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v6
        with:
          ref: ${{{{ github.event.inputs.version && format('v{{0}}', github.event.inputs.version) || github.ref }}}}
      - uses: astral-sh/setup-uv@v7
      - run: uv python install 3.12
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

### .github/workflows/tag.yml

```yaml
name: Tag

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches: [main]

jobs:
  tag:
    if: >
      github.event.workflow_run.conclusion == 'success' &&
      github.event.workflow_run.event == 'push'
    runs-on: ubuntu-latest
    permissions:
      contents: write
      actions: write
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 2
      - name: Check version
        id: version
        run: |
          CURRENT_VERSION=$(grep -m1 'version = ' pyproject.toml | cut -d'"' -f2)
          echo "current=$CURRENT_VERSION" >> $GITHUB_OUTPUT
          if curl -s "https://pypi.org/pypi/{package-name}/$CURRENT_VERSION/json" | grep -q '"version"'; then
            echo "on_pypi=true" >> $GITHUB_OUTPUT
          else
            echo "on_pypi=false" >> $GITHUB_OUTPUT
          fi
          git fetch --tags
          if git rev-parse "v$CURRENT_VERSION" >/dev/null 2>&1; then
            echo "tag_exists=true" >> $GITHUB_OUTPUT
          else
            echo "tag_exists=false" >> $GITHUB_OUTPUT
          fi
      - name: Create and push tag
        if: steps.version.outputs.on_pypi == 'false' && steps.version.outputs.tag_exists == 'false'
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git tag "v${{ steps.version.outputs.current }}"
          git push origin "v${{ steps.version.outputs.current }}"
      - name: Trigger publish
        if: steps.version.outputs.on_pypi == 'false'
        run: gh workflow run publish.yml -f version=${{ steps.version.outputs.current }} -R ${{ github.repository }}
        env:
          GH_TOKEN: ${{ github.token }}
      - name: Trigger docs
        if: steps.version.outputs.on_pypi == 'false' && steps.version.outputs.tag_exists == 'false'
        run: gh workflow run docs.yml --ref "v${{ steps.version.outputs.current }}" -R ${{ github.repository }}
        env:
          GH_TOKEN: ${{ github.token }}
```

### .github/workflows/docs.yml

```yaml
name: Docs

on:
  push:
    branches: [main]
    tags: ["v*"]
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
      - run: |
          git config user.name github-actions[bot]
          git config user.email github-actions[bot]@users.noreply.github.com
      - uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
          cache-dependency-glob: "pyproject.toml"
      - run: uv python install 3.12
      - run: uv sync --group docs
      - name: Deploy docs (version tag)
        if: startsWith(github.ref, 'refs/tags/v')
        run: |
          VERSION=${GITHUB_REF#refs/tags/v}
          uv run mike deploy --push --update-aliases $VERSION latest
          uv run mike set-default --push latest
      - name: Deploy docs (main branch)
        if: github.ref == 'refs/heads/main'
        run: uv run mike deploy --push main
```

### .github/workflows/dependabot-automerge.yml

```yaml
name: Dependabot Auto-merge

on: pull_request

permissions:
  contents: write
  pull-requests: write

jobs:
  automerge:
    runs-on: ubuntu-latest
    if: github.actor == 'dependabot[bot]'
    steps:
      - run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### .github/dependabot.yml

```yaml
version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      dev-dependencies:
        dependency-type: "development"
      production-dependencies:
        dependency-type: "production"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      actions:
        patterns: ["*"]
```

## Step 7: mkdocs.yml

```yaml
site_name: {Package Name}
site_description: {description}
site_url: https://oliverhaas.github.io/{package-name}/
repo_url: https://github.com/oliverhaas/{package-name}
repo_name: oliverhaas/{package-name}
edit_uri: edit/main/docs/

theme:
  name: material
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - navigation.instant
    - navigation.instant.progress
    - navigation.tracking
    - navigation.sections
    - content.code.copy

markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - pymdownx.superfences
  - admonition
  - pymdownx.details
  - toc:
      permalink: true

extra:
  version:
    provider: mike

nav:
  - Home: index.md
  - Getting Started:
      - Installation: getting-started/installation.md
  - Reference:
      - Changelog: reference/changelog.md
```

## Step 8: Other Files

### .gitignore

```
*.py[cod]
__pycache__/
*.egg-info
/build/
/dist/
*.swp
.idea
.venv
.coverage
coverage.xml
.mypy_cache
.ruff_cache
.pytest_cache
dump.rdb
CLAUDE.md
site/
*.sqlite3
.DS_Store
```

### .python-version

```
3.14
```

### {module_name}/__init__.py

```python
"""
{description}
"""
```

### {module_name}/py.typed

Empty file (PEP 561 marker).

### README.md

```markdown
# {package-name}

[![PyPI version](https://img.shields.io/pypi/v/{package-name}.svg?style=flat)](https://pypi.org/project/{package-name}/)
[![Python versions](https://img.shields.io/pypi/pyversions/{package-name}.svg)](https://pypi.org/project/{package-name}/)
[![CI](https://github.com/oliverhaas/{package-name}/actions/workflows/ci.yml/badge.svg)](https://github.com/oliverhaas/{package-name}/actions/workflows/ci.yml)

{description}

## Installation

```console
pip install {package-name}
```

## Documentation

Full documentation at [oliverhaas.github.io/{package-name}](https://oliverhaas.github.io/{package-name}/)

## License

MIT
```

### docs/index.md

```markdown
# {Package Name}

{description}
```

### docs/getting-started/installation.md

```markdown
# Installation

```console
pip install {package-name}
```
```

### docs/reference/changelog.md

```markdown
# Changelog

## 0.1.0a1 (Unreleased)

Initial release.
```

### tests/conftest.py (Django package)

```python
"""Pytest configuration."""
```

### tests/settings/base.py (Django package only)

```python
SECRET_KEY = "test-secret-key"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

USE_TZ = True
```

## Step 9: Initialize

```bash
# Initialize git if not already
git init

# Install dependencies
uv sync --group dev --group docs

# Install pre-commit hooks
uv run pre-commit install --install-hooks

# Initial commit
git add -A
git commit -m "feat: initial package scaffold"
git branch -M main
git remote add origin git@github.com:oliverhaas/{package-name}.git
git push -u origin main
```

## Step 10: Post-Setup (Manual)

Tell the user these need to be done manually:

1. **PyPI Trusted Publisher** - https://pypi.org/manage/account/publishing/
   - Owner: `oliverhaas`, Repository: `{package-name}`, Workflow: `publish.yml`, Environment: `pypi`

2. **GitHub Pages** - https://github.com/oliverhaas/{package-name}/settings/pages
   - Source: Deploy from a branch, Branch: `gh-pages` / `/ (root)`

3. **GitHub Environment** - https://github.com/oliverhaas/{package-name}/settings/environments/new
   - Create environment named `pypi`

4. **Codecov** - https://codecov.io/gh/oliverhaas/{package-name}

## Native Extensions (optional)

Apply on top of the standard scaffold when the package ships compiled code. For authoring guidance (footguns, pure-mode patterns, `Bound` vs `Py`, free-threading), see the `cython` and `pyo3` skills.

### Cython

Replace the `[build-system]` block in `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=77", "cython>=3.2"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
{module_name} = ["py.typed", "*.pxd"]

[tool.setuptools.exclude-package-data]
{module_name} = ["*.c", "*.html"]
```

Add `setup.py` (setuptools won't read `ext_modules` from `pyproject.toml` yet):

```python
"""Build hook: cythonize sources into C extensions."""

from Cython.Build import cythonize
from setuptools import setup

setup(
    ext_modules=cythonize(
        ["src/{module_name}/*.py"],
        compiler_directives={
            "language_level": "3str",
            "freethreading_compatible": True,
        },
    ),
)
```

Add `cython==3.2.4` to the `dev` dependency-group.

Add a cibuildwheel block (free-threaded cp314t alongside cp314):

```toml
[tool.cibuildwheel]
build = ["cp314-*", "cp314t-*"]
enable = ["cpython-freethreading"]
build-frontend = "build[uv]"
build-verbosity = 1
test-command = "python -c \"import {module_name}\""

[tool.cibuildwheel.linux]
archs = ["x86_64"]

[tool.cibuildwheel.macos]
archs = ["arm64"]
```

For Django packages where importing the module triggers app-loading, replace `test-command` with a `settings.configure(INSTALLED_APPS=[]); django.setup()` preamble.

`.gitignore` additions:

```
{module_name}/*.so
{module_name}/*.c
{module_name}/*.html
```

CI workflow note: setuptools editable installs do not auto-rebuild on `.py`/`.pyx` changes. The `test` job needs an explicit `uv pip install -e .` step after `uv sync` if tests import the compiled module.

### PyO3 / Rust

Two layouts. Pick the second only when the native code is an optional accelerator over a working pure-Python fallback.

**Single-package (default):** maturin builds the whole package.

```toml
[build-system]
requires = ["maturin>=1.7,<2.0"]
build-backend = "maturin"

[tool.maturin]
module-name = "{module_name}._native"
features = ["pyo3/extension-module"]
python-source = "python"
```

Layout: `python/{module_name}/__init__.py` for the Python facade, `Cargo.toml` and `src/lib.rs` at the repo root.

`Cargo.toml`:

```toml
[package]
name = "{package-name}"
version = "0.1.0"
edition = "2024"
publish = false

[lib]
name = "_native"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.28", features = ["extension-module"] }

[profile.release]
lto = true
strip = true
```

**Split-distribution (cachex pattern):** pure-Python parent (hatchling) plus an optional native sibling (maturin) under `crates/<crate-name>/`. Wire with `[tool.uv.workspace] members = ["crates/*"]` and `[tool.uv.sources] <crate-name> = { workspace = true }` so `uv sync` builds the crate locally. Stitch namespaces by setting `module-name = "{module_name}._driver"` in the crate's `[tool.maturin]` and adding `__path__ = extend_path(__path__, __name__)` to the parent `__init__.py`. See `django-cachex` for a working example.

Add a cibuildwheel block:

```toml
[tool.cibuildwheel]
build = ["cp314-*", "cp314t-*"]
enable = ["cpython-freethreading"]
build-verbosity = 1

[tool.cibuildwheel.linux]
archs = ["x86_64", "aarch64"]
before-all = "curl --proto =https --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal"
environment = { PATH = "$HOME/.cargo/bin:$PATH" }

[tool.cibuildwheel.macos]
archs = ["arm64"]

[tool.cibuildwheel.windows]
archs = ["AMD64"]
```

The `before-all` plus `environment.PATH` pair is required: manylinux containers don't ship Rust, and without `PATH` cibuildwheel can't find `cargo` after the install. macOS and Windows runners come with rustup preinstalled. For native aarch64 (no QEMU), use `runs-on: ubuntu-24.04-arm` in the workflow matrix instead of the default Linux runner.

`.gitignore` additions:

```
target/
*.so
__pycache__/
```

Add a smoke-test job that imports the wheel before publishing; for the split-distribution pattern, also add a smoke-test that asserts the pure path works *without* the native extension installed.
