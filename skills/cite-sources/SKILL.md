---
name: cite-sources
description: Don't assert framework, library, or domain facts from memory. Read the source or mark the claim uncertain. Use when stating how a framework/library behaves, or when answering "does X do Y?".
user-invocable: false
---

# Cite Sources, Don't Hallucinate

When stating a fact about Django, Celery, psycopg, Postgres, Tailwind, daisyUI, Playwright, pytest, or any other framework/library/domain object — read the source, the docs, or the project, or explicitly mark the claim uncertain. Don't invent.

## What "cite the source" looks like

- File + line number from the project: `apps/orders/models.py:42`.
- Docs URL: `https://docs.djangoproject.com/en/5.0/ref/models/...`.
- Source-of-truth read: the actual enum members, the actual settings, the actual migration.
- A `gh` / `grep` / `Read` call you ran, showing the output.

## What "mark it uncertain" looks like

- "I think this is how gunicorn `preload` works, but I haven't verified — check the docs before relying on it."
- "Unknown — this is project-specific config; check `chart/values.yaml`."

Both are acceptable. Confident assertions without evidence are not.

## Common hallucination categories

- **Enum / TextChoices values** invented from convention instead of read from the model.
- **Method names and signatures** ("`QuerySet.exists_or_create`") that don't exist.
- **Issue / PR / docs URLs** fabricated to look authoritative — never invent issue numbers.
- **Library internals** (Celery task lifecycle, psycopg connection pooling, Django admin `select_related(max_depth=5)`) asserted from memory when the actual behavior is one `grep` away in site-packages.
- **Version-specific syntax** ("Python 3.x added this", "Django 5.x requires that") asserted without checking.
- **Third-party API shapes** (vendor token prefixes, webhook payload schemas) without checking docs.

## When you do read the source

Quote the relevant line back so the user can audit. "I read `django/db/models/query.py:1234` — `prefetch_related` returns the queryset itself, no clone." is verifiable. "Django's prefetch_related returns the queryset" is unfalsifiable noise.
