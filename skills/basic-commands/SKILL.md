---
name: basic-commands
description: "Standard commands for projects scaffolded by `package-init`: uv, ruff, ty/mypy, pytest (markers, parallel, flake-finder), pre-commit, mkdocs, build, and Django management. Use when running or discussing project commands, debugging command failures, or setting up a dev environment."
user-invocable: false
---

# Basic Commands

All Python commands run through `uv run` so the project's locked environment is used. The conventions below match the scaffold from the `package-init` skill.

## One-Time Setup

```bash
uv sync --group dev --group docs
uv run pre-commit install --install-hooks
```

`uv sync` is also safe to run any time: it reconciles the venv with `pyproject.toml` + `uv.lock`.

## Tests

```bash
uv run pytest                   # default: excludes screenshot and benchmark markers
uv run pytest -n auto           # parallel via pytest-xdist
uv run pytest -n 4              # bounded parallelism (leaves cores for other work)
uv run pytest path/to/test.py   # one file
uv run pytest -k "name_substr"  # by name
uv run pytest -x --tb=short     # stop on first fail, short traceback
```

### Markers

The standard scaffold registers these:

```bash
uv run pytest -m unit                       # fast isolated tests
uv run pytest -m e2e                        # browser/integration
uv run pytest -m screenshot                 # visual regression (see tests-screenshot)
uv run pytest -m benchmark --codspeed       # perf benchmarks (see tests-benchmarks)
```

Defaults exclude `screenshot` and `benchmark` from the standard run.

### Flake check after writing a new test

```bash
uv run pytest --flake-finder --flake-runs=20 path/to/test_file.py
```

Bump `--flake-runs` to 100+ when investigating an existing flake (see `fix-flaky-test`).

## Lint and Format

```bash
uv run ruff check                       # report
uv run ruff check --fix                 # auto-fix
uv run ruff check --fix --unsafe-fixes  # include unsafe fixes
uv run ruff format                      # apply formatting
uv run ruff format --check              # CI: verify only
```

## Type Check

Pick the one configured in `pyproject.toml`:

```bash
uv run ty check {module}/    # non-Django packages
uv run mypy {module}/        # Django packages (uses django-stubs)
```

See `type-annotations` for the differences between the two checkers.

## Pre-commit

```bash
uv run pre-commit run --all-files                       # all pre-commit hooks
uv run pre-commit run --all-files --hook-stage pre-push # also runs the type-check hook
uv run pre-commit autoupdate                            # bump hook versions
```

## Dependency Management

```bash
uv sync                          # reconcile env with lockfile
uv add <package>                 # add a runtime dep
uv add --group dev <package>     # add a dev-only dep
uv add --group docs <package>    # add a docs-only dep
uv remove <package>              # remove
uv lock --upgrade                # refresh lockfile to latest compatible versions
uv tree                          # show dependency graph
```

## Docs (mkdocs + mike)

```bash
uv run mkdocs serve              # local preview at http://127.0.0.1:8000
uv run mkdocs build              # build static site to ./site/
uv run mike serve                # preview the multi-version site
```

Versioned deploys happen in CI; don't run `mike deploy` manually.

## Build and Publish

```bash
uv build                         # builds sdist + wheel into ./dist/
```

Publishing is automated by the `tag.yml` + `publish.yml` workflows on a version bump in `pyproject.toml`. Don't `uv publish` manually.

## Native Extensions

If the package has compiled code (Cython or PyO3), an editable install is required after `uv sync` so tests import the compiled module:

```bash
uv pip install -e .              # rebuild the native extension
```

For PyO3 split-distribution layouts (the `django-cachex` pattern), `uv sync` also drives the workspace crate build via maturin.

## Django Projects

```bash
uv run python manage.py runserver
uv run python manage.py shell                       # see django-shell-function
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python manage.py migrate --plan              # preview without applying
uv run python manage.py createsuperuser
uv run python manage.py collectstatic --noinput
uv run python manage.py <custom_command>            # see django-management-commands
```

## When a Command Fails

If a command exits with "command not found" or a missing-module error, the tool is likely not installed in the locked env. Don't skip the step or substitute another tool:

- Tool expected in `pyproject.toml`? Run `uv sync --group dev`.
- Type checker error after adding a dep? Re-sync, then re-run the checker.
- Native extension import error after editing `.pyx`/`.rs`? Re-run `uv pip install -e .`.
- Pre-commit hook failure? Investigate the underlying issue; never `--no-verify`.
- Management command that doesn't exist? Check the app's `management/commands/` directory for the actual name.
