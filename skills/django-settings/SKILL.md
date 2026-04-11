---
name: django-settings
description: App settings patterns, environment config, and secrets management. Use when adding configurable settings to a reusable app, structuring project settings, or managing secrets.
user-invocable: false
---

# Django Settings Guidelines

## App Settings (Reusable Packages)

For installable apps, expose settings with a `getattr(settings, ...)` wrapper. This avoids import-time failures and provides sensible defaults.

```python
# myapp/conf.py
from django.conf import settings

def _setting(name, default):
    return getattr(settings, name, default)

MYAPP_TIMEOUT = _setting("MYAPP_TIMEOUT", 30)
MYAPP_API_URL = _setting("MYAPP_API_URL", "https://api.example.com")
MYAPP_FEATURE_FLAGS = _setting("MYAPP_FEATURE_FLAGS", {})
```

Import from `conf.py` inside the app, never directly from `django.conf.settings`:

```python
# myapp/tasks.py
from .conf import MYAPP_TIMEOUT, MYAPP_API_URL  # correct
from django.conf import settings; settings.MYAPP_TIMEOUT  # wrong - bypasses defaults
```

**django-appconf pattern** for larger apps (auto-prefixes, lazy evaluation):

```python
# myapp/conf.py
from appconf import AppConf

class MyAppConf(AppConf):
    TIMEOUT = 30
    API_URL = "https://api.example.com"
    MAX_RETRIES = 3

    class Meta:
        prefix = "myapp"  # MYAPP_TIMEOUT, MYAPP_API_URL, etc.

# Usage anywhere in myapp:
from myapp.conf import settings as myapp_settings
timeout = myapp_settings.MYAPP_TIMEOUT
```

AppConf reads lazily - safe to import at module level.

---

## Environment Config

### django-environ (preferred)

```python
# settings.py
import environ

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    DATABASE_URL=(str, "sqlite:///db.sqlite3"),
)

environ.Env.read_env()  # reads .env if present; safe to call unconditionally

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
DATABASES = {"default": env.db()}  # parses DATABASE_URL
CACHES = {"default": env.cache("CACHE_URL")}  # parses CACHE_URL
EMAIL_CONFIG = env.email("EMAIL_URL")  # parses EMAIL_URL
```

Type coercions built in: `env.bool()`, `env.int()`, `env.list()`, `env.json()`.

### os.environ (when no extra deps allowed)

```python
import os

SECRET_KEY = os.environ["SECRET_KEY"]  # KeyError if missing - intentional
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",") if os.environ.get("ALLOWED_HOSTS") else []
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///db.sqlite3")
```

Prefer `os.environ["KEY"]` (hard fail) over `os.environ.get("KEY")` for required vars - fail loudly at startup.

---

## Settings File Organization

### Single file with env vars (default choice)

Simplest approach. Works for most projects.

```
project/
├── settings.py
├── .env              # local overrides, gitignored
└── .env.example      # template, committed
```

```python
# settings.py
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
# ...
```

### Base/dev/prod split (when environments diverge significantly)

Use only when dev and prod have meaningfully different installed apps, middleware, or third-party integrations.

```
config/
├── settings/
│   ├── __init__.py   # empty or re-exports base
│   ├── base.py       # shared settings
│   ├── dev.py        # imports base, overrides
│   └── prod.py       # imports base, overrides
```

```python
# settings/base.py
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env()

INSTALLED_APPS = [
    "django.contrib.admin",
    # ...
    "myapp",
]

# settings/dev.py
from .base import *  # noqa: F401,F403

DEBUG = True
INSTALLED_APPS += ["debug_toolbar", "django_extensions"]
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE

# settings/prod.py
from .base import *  # noqa: F401,F403

DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

Select at runtime via `DJANGO_SETTINGS_MODULE=config.settings.prod`.

**Do not split** just to have different `DEBUG` values - that's what env vars are for.

---

## Typed Settings Access

For type safety without a full framework, wrap access explicitly:

```python
# myapp/conf.py
from django.conf import settings

def get_timeout() -> int:
    val = getattr(settings, "MYAPP_TIMEOUT", 30)
    if not isinstance(val, int):
        raise ImproperlyConfigured("MYAPP_TIMEOUT must be an integer")
    return val

def get_api_url() -> str:
    val = getattr(settings, "MYAPP_API_URL", "https://api.example.com")
    if not isinstance(val, str):
        raise ImproperlyConfigured("MYAPP_API_URL must be a string")
    return val
```

For project settings with django-environ, types come from `Env()` declarations - no runtime isinstance checks needed.

---

## Settings Validation at Startup

Use `AppConfig.ready()` to validate required settings before the app processes any requests:

```python
# myapp/apps.py
from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured

class MyAppConfig(AppConfig):
    name = "myapp"

    def ready(self):
        self._validate_settings()

    def _validate_settings(self):
        from django.conf import settings

        required = ["MYAPP_API_KEY", "MYAPP_WEBHOOK_SECRET"]
        missing = [k for k in required if not getattr(settings, k, None)]
        if missing:
            raise ImproperlyConfigured(
                f"Missing required settings: {', '.join(missing)}"
            )

        timeout = getattr(settings, "MYAPP_TIMEOUT", 30)
        if not isinstance(timeout, int) or timeout <= 0:
            raise ImproperlyConfigured("MYAPP_TIMEOUT must be a positive integer")
```

`ready()` runs after the app registry is fully populated. Import models inside `ready()` (or `_validate_settings()`) if needed to avoid AppRegistryNotReady.

---

## Secret Management

### Development

Keep secrets in `.env`, never committed:

```
# .env (gitignored)
SECRET_KEY=dev-only-key-not-for-production
DATABASE_URL=postgres://user:pass@localhost/mydb
STRIPE_SECRET_KEY=sk_test_...
```

Commit `.env.example` with placeholders and types:

```
# .env.example
SECRET_KEY=                    # required: Django secret key
DATABASE_URL=sqlite:///db.sqlite3  # optional: defaults to SQLite
STRIPE_SECRET_KEY=             # required for payments
DEBUG=false
```

### Production

Prefer environment variables injected by the platform (Heroku, Railway, Fly.io, Kubernetes secrets). Never store secrets in:
- Version control (even in private repos)
- Settings files (even prod.py)
- Docker images

For AWS: use Secrets Manager or Parameter Store and fetch at startup:

```python
# settings.py (AWS example)
import boto3, json

def _get_secret(name: str) -> dict:
    client = boto3.client("secretsmanager")
    return json.loads(client.get_secret_value(SecretId=name)["SecretString"])

if not DEBUG:
    _secrets = _get_secret("myapp/prod")
    SECRET_KEY = _secrets["django_secret_key"]
    DATABASES["default"]["PASSWORD"] = _secrets["db_password"]
```

---

## Common Pitfalls

### Mutable defaults

```python
# Wrong - shared mutable object across all consumers
MYAPP_FEATURE_FLAGS = _setting("MYAPP_FEATURE_FLAGS", {})

# If consumers mutate the dict they share state. Fix: copy on access
def get_feature_flags() -> dict:
    return dict(getattr(settings, "MYAPP_FEATURE_FLAGS", {}))
```

Same issue with list defaults. Use tuples for immutable defaults or copy on access.

### Import-time settings access

```python
# Wrong - evaluated when module is imported, before settings are configured
# myapp/utils.py
from django.conf import settings
TIMEOUT = settings.MYAPP_TIMEOUT  # ImproperlyConfigured in tests, setup tools, etc.

# Correct - access inside functions/methods
def get_timeout() -> int:
    return getattr(settings, "MYAPP_TIMEOUT", 30)
```

Import-time access breaks `manage.py` commands, test setup, and any tooling that imports your module before calling `django.setup()`.

### Hardcoded paths in settings

```python
# Wrong
BASE_DIR = "/home/deploy/myproject"
MEDIA_ROOT = "/home/deploy/myproject/media"

# Correct
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_ROOT = BASE_DIR / "media"
```

### DATABASE_URL not set in CI

Add `DATABASE_URL` to CI env vars explicitly. Don't rely on a default SQLite path - tests should mirror prod DB behavior where possible.

### Accidental settings mutation in tests

```python
# tests/test_something.py
from django.test import TestCase, override_settings

class MyTest(TestCase):
    @override_settings(MYAPP_TIMEOUT=5)
    def test_timeout_respected(self):
        # settings are restored after test
        ...
```

Never assign directly to `settings.MYAPP_TIMEOUT` in tests - changes persist across the test session.

---

## Summary

- **Reusable apps**: wrap with `getattr(settings, "APP_KEY", default)` in `conf.py`; validate in `AppConfig.ready()`
- **Project settings**: use django-environ for type-safe env var access
- **Organization**: single `settings.py` + env vars by default; split to base/dev/prod only when environments differ structurally
- **Secrets**: `.env` locally (gitignored), platform env vars or secrets manager in prod
- **Mutable defaults**: use tuples or copy-on-access functions
- **Import-time access**: always access settings inside functions, never at module level

---
