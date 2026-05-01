---
name: packages
description: Preferred and useful packages reference. Consult when choosing dependencies or looking up package names.
user-invocable: false
---

# Preferred Packages

## Our Packages

- `django-filthyfields` - fork of django-dirtyfields, field-level dirty tracking for models
- `django-formwork` - form widgets (SearchSelect, MultiSelect, ComboBox), HTMX integration
- `django-cachex` - improved django-redis cache backend
- `django-celeryx` - improved Celery Django integration
- `django-nplus1` - N+1 query detection
- `django-templates-cythonized` - Cython-compiled Django template engine for faster rendering
- `celery-redis-plus` - improved Celery Redis transport, use as default broker/backend
- `celery-asyncio` - asyncio rewrite of Celery

## Django Core

- `django` - web framework
- `django-health-check` - health check endpoints for monitoring
## Django Database

- `django-pg-zero-downtime-migrations` - safe Postgres migrations without downtime
- `django-syzygy` - staged deployable migrations (pre-deploy, post-deploy)
- `django-pghistory` - Postgres-based model history tracking via triggers
- `django-pgtrigger` - Postgres trigger management for Django models
- `django-cachalot` - ORM query caching via Redis

## Django Admin

- `django-import-export` - import/export data in admin (CSV, Excel, JSON)

## Django Auth & Users

- `django-allauth` - authentication, registration, social login
- `django-waffle` - feature flags, switches, and samples

## Django Models & Data

- `django-dirtyfields` - field-level change tracking, prefer our fork `django-filthyfields`
- `django-fsm-2` - finite state machine for model fields
- `django-tree-queries` - hierarchical/tree models using recursive CTEs, simpler than django-mptt

## Django API

- `django-ninja` - fast API framework for Django using Pydantic
- `pydantic` - data validation and serialization

## Django Templates & Frontend

- `django-htmx` - HTMX integration (middleware, request helpers)
- `django-vite` - Vite.js asset integration

## Django PDF & Email

- `django-anymail` - transactional email via ESPs (Mailgun, SES, etc.)

## Celery & Tasks

- `celery` - distributed task queue, use with `redis` and `zstd` extras
- `django-celery-beat` - database-backed periodic task scheduler

## HTTP & APIs

- `httpx` - modern HTTP client (async, HTTP/2), preferred over requests for new code
- `beautifulsoup4` - HTML/XML parsing and scraping

## Data & Serialization

- `pandas` - DataFrames for data analysis and transformation
- `numpy` - numerical computing
- `openpyxl` - read/write Excel files
- `glom` - nested data access and transformation

## Security & Encoding

- `python-dotenv` - load `.env` files into environment


## Monitoring & Logging

- `logtail-python` - Better Stack log ingestion, provides LogtailHandler for Python logging
- `psutil` - system/process monitoring

## Images

- `pillow` - image processing (resize, crop, convert)

## Retry & Resilience

- `tenacity` - retry with exponential backoff, jitter, custom conditions

## Production

- `granian` - Rust-based HTTP server for Python (ASGI/WSGI/RSGI)
- `psycopg` - PostgreSQL adapter, use `[c]` in prod, `[binary]` in dev
- `django-storages` - file storage backends (S3, GCS, Azure), use with `[s3]`
- `whitenoise` - static file serving, use with `[brotli]`

## Dev & Testing

- `pytest` - test framework
- `pytest-django` - Django integration for pytest
- `pytest-xdist` - parallel test execution
- `pytest-cov` - coverage reporting
- `pytest-flakefinder` - detect flaky tests by running them repeatedly
- `pytest-split` - split tests across CI workers
- `pytest-playwright` - Playwright browser testing for pytest
- `factory-boy` - test fixtures via factory pattern
- `testcontainers` - Docker containers for integration tests
- `time-machine` - mock `datetime.now()` and time-related functions
- `coverage` - code coverage measurement
- `django-coverage-plugin` - coverage for Django templates

## Code Quality

- `ruff` - fast Python linter and formatter
- `mypy` - static type checker
- `django-stubs` - type stubs for Django
- `djlint` - HTML template linter and formatter
- `pre-commit` - git hook manager for linters and formatters
- `commitizen` - conventional commit enforcement

## Debugging

- `debugpy` - Python debugger for VS Code
