---
name: tests-benchmarks
description: Performance benchmarks with pytest-codspeed (local mode). Use when writing or running performance tests, comparing implementations, or gating timing-sensitive tests behind a flag.
user-invocable: false
---

# Performance Benchmarks

Use `pytest-codspeed` for any test that measures wall-clock performance. The plugin handles warmup, repeats, and statistics, and prints a results table to the terminal. Trend tracking across runs is currently external — capture stdout if you need a record, or opt into the CodSpeed cloud platform later.

## Basic Pattern

Two API styles, both via the `benchmark` fixture / `@pytest.mark.benchmark` marker:

```python
import pytest

# Marker: measures the entire test function
@pytest.mark.benchmark
def test_bulk_import(db):
    items = [ItemFactory.build() for _ in range(1_000)]
    Item.objects.bulk_create(items)

# Fixture: measures only the wrapped call
@pytest.mark.benchmark
def test_bulk_import_throughput(db, benchmark):
    items = [ItemFactory.build() for _ in range(1_000)]
    benchmark(Item.objects.bulk_create, items)
```

The marker and fixture are independent. Apply `@pytest.mark.benchmark` explicitly even when using the fixture — the fixture does not auto-mark, and the marker is what `-m benchmark` and the default-CI filter rely on.

## Per-test Config

The marker takes no arguments. Per-test tuning lives on the fixture's `pedantic` mode:

```python
@pytest.mark.benchmark
def test_zadd(benchmark, cache):
    benchmark.pedantic(
        cache.zadd,
        args=("k", {"m": 1}),
        rounds=100,
        iterations=10,
        warmup_rounds=5,
    )
```

`setup` returns `(args, kwargs)` for dynamic per-round inputs:

```python
def setup():
    return (OrderFactory.create_batch(100),), {}

benchmark.pedantic(process_orders, setup=setup, rounds=5, iterations=3)
```

**No grouping.** pytest-codspeed has no `group=` equivalent in local mode — A/B comparisons are read row-by-row in the terminal table, with no relative-speedup column. Split the two implementations into separate test functions, run them in the same session, and eyeball.

## Selection

```bash
uv run pytest -m benchmark --codspeed       # measure benchmarks
uv run pytest -m benchmark                  # smoke check: run them without measurement
uv run pytest -m "not benchmark"            # skip benchmarks (default CI)
```

The middle form is the equivalent of pytest-benchmark's `--benchmark-disable`: marked tests run as ordinary pytest tests when `--codspeed` is absent. Useful to confirm benchmarks haven't bit-rotted without paying the measurement cost.

## Measurement Modes

`--codspeed-mode` defaults to `auto`, which picks `walltime` locally and the appropriate instrument when running inside CodSpeed CI. For routine local use, walltime is what you'll get.

| Mode | When | Requires |
|---|---|---|
| `auto` | Default. Picks `walltime` locally. | Nothing |
| `walltime` | Fast feedback, cross-platform. | Nothing |
| `simulation` | Deterministic CPU-cycle counts; use for noise-sensitive comparisons. | Linux + valgrind |
| `memory` | Heap allocation tracking. | Linux + valgrind |

```bash
uv run pytest -m benchmark --codspeed                              # walltime
uv run pytest -m benchmark --codspeed --codspeed-mode simulation   # cycles
uv run pytest -m benchmark --codspeed --codspeed-warmup-time 1 --codspeed-max-time 5
```

Capture output as a poor-man's history when needed:

```bash
uv run pytest -m benchmark --codspeed | tee benchmarks/$(date +%Y-%m-%d).log
```

## Gating in CI

Skip benchmarks by default so normal `pytest` and CI runs stay fast:

```toml
[tool.pytest.ini_options]
addopts = "-m 'not screenshot and not benchmark'"
markers = [
    "benchmark: pytest-codspeed performance benchmarks, run with --codspeed",
]
```

Run them explicitly with `pytest -m benchmark --codspeed` when you want to measure. Register the marker explicitly even though pytest-codspeed registers it on install — the entry documents intent and matches the convention in `tests-general`.

## File Layout

Benchmarks live in the same `test_<feature>.py` file as the rest of that feature's tests — one module per feature, distinguish test types by marker. Don't split benchmarks into a separate `tests/benchmarks/` directory or `test_benchmarks_*.py` file; the marker is what the selection flags filter on, and keeping a feature's tests together makes them easy to find and run as a unit.

Always apply `@pytest.mark.benchmark` explicitly — the fixture does not auto-mark, and the marker is what the default-CI exclusion and `-m benchmark` rely on.

## Caveats

- The `benchmark` fixture can be called only once per test function. Split A/B comparisons into separate test functions.
- `simulation` and `memory` modes require valgrind and only work on Linux. macOS dev machines are walltime-only.
- Walltime is non-deterministic; expect rel-stddev around a few percent on a quiet machine, more under load.

## When NOT to Use

- Single threshold checks ("must complete in under 50ms"): a plain `time.perf_counter()` and an assert is enough.
- Custom human-readable summary at the end of the run: implement `pytest_terminal_summary` in `conftest.py` and collect timings via a small fixture instead.
