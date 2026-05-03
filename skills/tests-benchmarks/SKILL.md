---
name: tests-benchmarks
description: Performance benchmarks with pytest-benchmark. Use when writing or running performance tests, comparing implementations, or gating timing-sensitive tests behind a flag.
user-invocable: false
---

# Performance Benchmarks

Use `pytest-benchmark` for any test that measures wall-clock performance. The plugin handles warmup, repeats, and statistics (min/max/mean/stddev), and emits JSON for trend tracking.

## Basic Pattern

```python
def test_bulk_import_throughput(db, benchmark):
    items = [ItemFactory.build() for _ in range(1_000)]
    benchmark(Item.objects.bulk_create, items)
```

The `benchmark` fixture runs the callable repeatedly and prints a timing table. Tests using the fixture are auto-marked with `@pytest.mark.benchmark`, so selection flags work without an explicit decorator.

## Per-test Config

Tune rounds, timing, warmup, and grouping via the marker:

```python
@pytest.mark.benchmark(
    group="zadd",
    min_rounds=100,
    max_time=2.0,
    warmup=True,
)
def test_zadd_default(benchmark, cache):
    benchmark(cache.zadd, "k", {"m": 1})

@pytest.mark.benchmark(group="zadd")
def test_zadd_pipelined(benchmark, cache):
    benchmark(pipelined_zadd, cache, "k", {"m": 1})
```

`group=` is the most useful argument: it bundles related benchmarks into a sub-table with relative comparisons (`1.00x` vs `3.42x slower`). Use it when comparing implementations of the same operation.

## Selection

```bash
uv run pytest --benchmark-only      # run only benchmarks
uv run pytest --benchmark-skip      # skip them
uv run pytest --benchmark-disable   # run them but no timing (smoke check)
```

## Gating in CI

Skip benchmarks by default so normal `pytest` and CI runs stay fast:

```toml
[tool.pytest.ini_options]
addopts = "--benchmark-skip"
```

Run them explicitly with `pytest --benchmark-only` when you want to measure.

Don't manually register a `benchmark` marker in `pyproject.toml` — pytest-benchmark registers it on install.

## File Layout

Benchmarks can live alongside regular tests, but for long-running suites prefer their own files (`test_benchmarks_*.py`) or directory (`tests/benchmarks/`). Auto-marking from the fixture means `--benchmark-only` and `--benchmark-skip` work either way.

## When NOT to Use

- Single threshold checks ("must complete in under 50ms"): a plain `time.perf_counter()` and an assert is enough.
- Custom human-readable summary at the end of the run: implement `pytest_terminal_summary` in `conftest.py` and collect timings via a small fixture instead.
