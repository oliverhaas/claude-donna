---
name: django-management-commands
description: Management command patterns for Django. Use when writing, reviewing, or testing custom management commands.
user-invocable: false
---

# Django Management Commands

Management commands are the right tool for one-off operations, scheduled jobs, data migrations run manually, and administrative tasks. They run in the full Django context, have access to the ORM, and can be invoked from cron, CI, or the shell.

## Basic Structure

```python
# myapp/management/commands/sync_products.py
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sync products from external API"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
        parser.add_argument("--limit", type=int, default=None, help="Max records to process")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        limit = options["limit"]

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run: no changes will be written"))

        # main logic here
        self.stdout.write(self.style.SUCCESS("Done"))
```

Required directory structure:

```
myapp/
  management/
    __init__.py
    commands/
      __init__.py
      sync_products.py
```

Both `__init__.py` files must exist. Django will not discover the command otherwise.

## Argument Parsing

Use `add_arguments` with standard argparse patterns. Always add `help=` strings.

```python
def add_arguments(self, parser):
    # Positional argument
    parser.add_argument("username", type=str)

    # Optional flag
    parser.add_argument("--dry-run", action="store_true")

    # Optional value with default
    parser.add_argument("--batch-size", type=int, default=500)

    # Required named argument
    parser.add_argument("--tenant-id", type=int, required=True)

    # Multiple values
    parser.add_argument("--ids", nargs="+", type=int)

    # Choices
    parser.add_argument("--status", choices=["active", "inactive"], default="active")
```

Access in `handle` via `options["dry_run"]` (argparse converts hyphens to underscores automatically).

## Output Patterns

Use `self.stdout` and `self.stderr`, not `print`. This allows output to be captured in tests and redirected cleanly.

```python
# Normal output
self.stdout.write("Processing records...")

# Styled output
self.stdout.write(self.style.SUCCESS("Created 42 records"))
self.stdout.write(self.style.WARNING("Skipping 3 duplicates"))
self.stdout.write(self.style.ERROR("Failed to process record 99"))
self.stdout.write(self.style.NOTICE("Info: running in dry-run mode"))

# Error output (goes to stderr)
self.stderr.write("Something went wrong")

# Verbosity-gated output (see Verbosity section)
if options["verbosity"] >= 2:
    self.stdout.write(f"  Detail: processed item {item.pk}")
```

Available styles: `SUCCESS` (green), `WARNING` (yellow), `ERROR` (red), `NOTICE` (magenta), `HTTP_INFO`, `HTTP_SUCCESS`, `HTTP_REDIRECT`, `HTTP_NOT_MODIFIED`, `HTTP_BAD_REQUEST`, `HTTP_NOT_FOUND`, `HTTP_SERVER_ERROR`, `MIGRATE_HEADING`, `MIGRATE_LABEL`, `SQL_FIELD`, `SQL_COLTYPE`, `SQL_KEYWORD`, `SQL_TABLE`.

## Error Handling and Exit Codes

Raise `CommandError` to abort with a non-zero exit code and an error message. Do not call `sys.exit()` directly.

```python
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    def handle(self, *args, **options):
        tenant_id = options["tenant_id"]

        try:
            tenant = Tenant.objects.get(pk=tenant_id)
        except Tenant.DoesNotExist:
            raise CommandError(f"Tenant {tenant_id} not found")

        try:
            result = external_api.sync(tenant)
        except ExternalAPIError as exc:
            raise CommandError(f"API error: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Synced {result.count} records"))
```

`CommandError` prints the message to stderr and exits with code 1. For partial failures where you want to continue processing, collect errors and raise at the end:

```python
errors = []
for item in queryset:
    try:
        process(item)
    except Exception as exc:
        errors.append(f"  {item.pk}: {exc}")

if errors:
    self.stderr.write(self.style.ERROR(f"{len(errors)} items failed:"))
    for msg in errors:
        self.stderr.write(msg)
    raise CommandError("Completed with errors")
```

## Transaction Management

Wrap the entire operation in a transaction when the command must be all-or-nothing. Use `dry_run` with `transaction.set_rollback(True)` to preview without committing.

```python
from django.db import transaction


class Command(BaseCommand):
    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        with transaction.atomic():
            count = self._run(options)
            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING(f"Dry run: would have processed {count} records"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Processed {count} records"))

    def _run(self, options):
        # all DB writes happen here
        ...
```

For commands that process large data sets, avoid one giant transaction. Use chunked commits instead:

```python
def handle(self, *args, **options):
    batch_size = options["batch_size"]
    qs = Product.objects.filter(needs_sync=True).iterator(chunk_size=batch_size)

    total = 0
    for batch in chunked(qs, batch_size):
        with transaction.atomic():
            for product in batch:
                sync_product(product)
                total += 1
        self.stdout.write(f"  {total} processed...", ending="\r")
        self.stdout.flush()
```

A simple chunking helper if not available from your utils:

```python
from itertools import islice

def chunked(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk
```

## Verbosity Levels

Django passes `--verbosity` (0-3) automatically. Use it to gate detail output without custom flags.

```python
def handle(self, *args, **options):
    verbosity = options["verbosity"]

    # verbosity 0: silent except errors
    # verbosity 1: normal (default)
    # verbosity 2: verbose
    # verbosity 3: very verbose

    self.stdout.write("Starting sync...")  # always shown (v1+)

    for item in queryset:
        process(item)
        if verbosity >= 2:
            self.stdout.write(f"  Processed: {item}")

    self.stdout.write(self.style.SUCCESS("Done"))

    if verbosity >= 1:
        self.stdout.write(f"Total: {total} records in {elapsed:.1f}s")
```

## Progress Reporting for Long-Running Commands

For commands that process many records, give feedback so operators know it is not hung.

```python
import time


class Command(BaseCommand):
    def handle(self, *args, **options):
        verbosity = options["verbosity"]
        qs = Order.objects.filter(status="pending")
        total = qs.count()
        processed = 0
        failed = 0
        start = time.monotonic()

        for order in qs.iterator():
            try:
                process_order(order)
                processed += 1
            except Exception as exc:
                failed += 1
                if verbosity >= 2:
                    self.stderr.write(f"  Failed {order.pk}: {exc}")

            if verbosity >= 1 and processed % 100 == 0:
                elapsed = time.monotonic() - start
                rate = processed / elapsed if elapsed else 0
                self.stdout.write(
                    f"  {processed}/{total} ({rate:.0f}/s)...",
                    ending="\r",
                )
                self.stdout.flush()

        elapsed = time.monotonic() - start
        self.stdout.write("")  # clear the \r line
        summary = f"Done: {processed} processed, {failed} failed in {elapsed:.1f}s"
        if failed:
            self.stdout.write(self.style.WARNING(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))
```

## Idempotent Commands

Commands should be safe to run multiple times. Prefer `update_or_create` / `get_or_create`, or explicit existence checks.

```python
def handle(self, *args, **options):
    created = 0
    skipped = 0

    for row in load_data():
        _, was_created = Product.objects.update_or_create(
            sku=row["sku"],
            defaults={
                "name": row["name"],
                "price": row["price"],
            },
        )
        if was_created:
            created += 1
        else:
            skipped += 1

    self.stdout.write(
        self.style.SUCCESS(f"Done: {created} created, {skipped} updated")
    )
```

If the command has side effects (email sends, API calls), use a flag column or idempotency key to skip already-processed records:

```python
qs = Order.objects.filter(confirmation_sent_at__isnull=True)
```

## Common Patterns

### Dry-Run Flag

The most useful flag for destructive or expensive commands. Always implement it for commands that write data.

```python
def add_arguments(self, parser):
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")

def handle(self, *args, **options):
    dry_run = options["dry_run"]

    with transaction.atomic():
        count = self._process()
        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING(f"Dry run complete: would have changed {count} records"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Changed {count} records"))
```

### Scoping by Tenant / Object

```python
def add_arguments(self, parser):
    parser.add_argument("--tenant-id", type=int, default=None, help="Limit to one tenant")

def handle(self, *args, **options):
    qs = Subscription.objects.all()
    if options["tenant_id"]:
        qs = qs.filter(tenant_id=options["tenant_id"])
    ...
```

### Delegating to Services

Keep `handle` thin. Business logic belongs in services.

```python
from myapp.services import SubscriptionService


class Command(BaseCommand):
    def handle(self, *args, **options):
        expired = Subscription.objects.filter(status="active", end_date__lt=date.today())
        count = 0
        for sub in expired:
            SubscriptionService.subscription_expire(subscription=sub)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Expired {count} subscriptions"))
```

## Testing Management Commands

Use `call_command` from `django.core.management`. Capture output by passing `StringIO` objects.

```python
import pytest
from io import StringIO
from django.core.management import call_command


@pytest.mark.django_db
def test_sync_products_creates_missing():
    stdout = StringIO()
    call_command("sync_products", stdout=stdout)
    output = stdout.getvalue()
    assert "Done" in output
    assert Product.objects.filter(source="external").exists()


@pytest.mark.django_db
def test_sync_products_dry_run_makes_no_changes():
    stdout = StringIO()
    call_command("sync_products", "--dry-run", stdout=stdout)
    assert not Product.objects.filter(source="external").exists()
    assert "Dry run" in stdout.getvalue()


@pytest.mark.django_db
def test_sync_products_missing_tenant_raises():
    with pytest.raises(SystemExit):
        call_command("sync_products", "--tenant-id", "99999")
```

`CommandError` is re-raised as `SystemExit` when using `call_command`. Catch `SystemExit` (not `CommandError`) in tests.

For checking stderr:

```python
@pytest.mark.django_db
def test_command_reports_failures():
    stderr = StringIO()
    # Provide a bad record that will fail
    OrderFactory.create(status="corrupt")
    call_command("process_orders", stderr=stderr)
    assert "Failed" in stderr.getvalue()
```

Test idempotency explicitly:

```python
@pytest.mark.django_db
def test_sync_products_idempotent():
    call_command("sync_products")
    count_after_first = Product.objects.count()
    call_command("sync_products")
    assert Product.objects.count() == count_after_first
```

---
