---
name: pyo3
description: "PyO3 0.23+ authoring patterns and footguns. Use when writing or reviewing #[pyfunction]/#[pyclass] code, GIL handling, error conversion, free-threading support, or PyO3-specific build configuration."
user-invocable: false
---

# PyO3

Authoring guide for PyO3 0.23+ Rust extensions. For scaffolding a new package with a Rust extension (maturin, cibuildwheel, cargo profile, gitignore), see `package-init`.

## Check the Rust crate's typed API first

Before wrapping a Rust crate by calling `call_method` / manual command dispatch from Python, look at the crate's typed surface. Crates like `redis` (TypedCommands), `sqlx`, `tonic`, etc. expose strongly-typed methods that map cleanly to PyO3 wrappers. Using them gives you the crate's type checks and panics-as-errors for free.

```rust
// Wrong: dynamic dispatch by string, throws away every type guarantee
conn.send_packed_command(&cmd("HSET").arg(key).arg(field).arg(value))?;

// Right: typed command surface
conn.hset(key, field, value)?;
```

If the typed primitive is genuinely missing, then implement the manual wrapper. Verify the gap first. Same principle as `general-python` → "Check the Library First".

## Layout: thin bindings crate, fat Rust core

Keep `#[pyfunction]`/`#[pyclass]` in one small bindings crate. Put real logic in plain Rust crates with no PyO3 dependency. Two payoffs: `cargo test` runs the core without an embedded interpreter, and the Python boundary stays small enough to audit.

```
crates/
  core/                  # plain Rust, no pyo3
    Cargo.toml
    src/lib.rs
  bindings/              # the only crate with pyo3
    Cargo.toml           # crate-type = ["cdylib"], pyo3 with extension-module feature-gated
    src/lib.rs           # #[pymodule] re-exports
```

In `crates/bindings/Cargo.toml`, feature-gate `pyo3/extension-module` so `cargo test` and `cargo build` work standalone:

```toml
[features]
default = []
extension-module = ["pyo3/extension-module"]

[dependencies]
pyo3 = { version = "0.28", default-features = false, features = ["macros"] }
```

Maturin then builds with `--features extension-module`.

## `Bound<'py, T>` for borrows; `Py<T>` for storage

PyO3 0.25 removed the old gil-ref API. Two handle types now:

- **`Bound<'py, T>`** is a refcount handle tied to a `Python<'py>` token. Use it for function args, locals, and short-lived returns. `.clone()` is cheap (refcount bump).
- **`Py<T>`** is GIL-independent. Use it when storing a Python object in a `#[pyclass]` field, in a global, or sending across `allow_threads`. Prefer `Py::clone_ref(py)` for clarity (`.clone()` works since 0.23 but reads ambiguously).

`Bound` lifetime-locks you to one GIL acquisition; `Py` does not. Convert with `.unbind()` and `.bind(py)`.

`IntoPy<T>` is deprecated in favour of `IntoPyObject` (0.23+). New code uses the `IntoPyObject` derive.

## Free-threading: mark the module, freeze the classes

For cp313t/cp314t compatibility, declare the module GIL-free and prefer frozen classes:

```rust
#[pymodule(gil_used = false)]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Counter>()?;
    Ok(())
}

#[pyclass(frozen)]
struct Counter { value: AtomicU64 }
```

`frozen` blocks `&mut self` access from Python, so you do interior mutability with `Atomic*` / `Mutex` and don't fight the borrow checker on the Python boundary. Without `gil_used = false`, importing under a free-threaded interpreter re-enables the GIL and emits a `RuntimeWarning`.

## `py.allow_threads(...)` for CPU-bound work

Release the GIL for any Rust work that doesn't touch Python:

```rust
#[pyfunction]
fn crunch(py: Python<'_>, data: Vec<u64>) -> u64 {
    py.allow_threads(|| heavy_compute(&data))
}
```

The closure must be `Send`; `Rc`/`RefCell`/raw pointers won't cross. Even on free-threaded Python this is still the right move: it detaches from the runtime and lets other threads progress.

**Drop ordering footgun:** never let a `Py<T>` get dropped inside `allow_threads`. Its `Drop` re-acquires the GIL; under contention you can deadlock. Take ownership before the closure or batch-drop after.

## Errors: `thiserror` plus `From<MyError> for PyErr`, never panic across FFI

Map domain errors to specific exception classes:

```rust
use pyo3::exceptions::{PyConnectionError, PyOSError, PyValueError};

#[derive(thiserror::Error, Debug)]
pub enum DriverError {
    #[error("bad input: {0}")] Bad(String),
    #[error(transparent)] Io(#[from] std::io::Error),
}

impl From<DriverError> for PyErr {
    fn from(e: DriverError) -> Self {
        match e {
            DriverError::Bad(m) => PyValueError::new_err(m),
            DriverError::Io(e)  => PyOSError::new_err(e.to_string()),
        }
    }
}
```

Then `#[pyfunction] fn op(...) -> Result<T, DriverError>` and `?` propagates. For long-running Rust loops, call `Python::check_signals(py)?` periodically so Ctrl-C reaches the user; otherwise the keypress is buffered until the function returns.

Panicking across the FFI boundary is undefined; convert to `PyErr` instead.

## Method-level macros worth knowing

The annotations that matter day-to-day:

- `#[pyo3(signature = (a, b=1, *, key=None))]` for explicit Python signatures with defaults, keyword-only, and `*args`/`**kwargs`. Use this on every non-trivial method; the inferred signature drops defaults silently.
- `#[pyo3(get, set)]` on `#[pyclass]` fields for Python-side property access.
- `#[pyclass(frozen)]` (free-threading + thread safety), `weakref`, `dict`, `subclass` for the obvious capabilities.
- `#[pymethods]` is the only place methods become Python-visible. Methods on a separate `impl` block are Rust-only; this is the most common refactor mistake.

## Type stubs

Ship a `.pyi` next to the compiled module plus a `py.typed` marker. For anything beyond a handful of functions, generate them with `pyo3-stub-gen` and gate drift in CI:

```bash
cargo run --bin stub_gen
git diff --exit-code
```

Hand-written stubs work for small surfaces but drift; generation requires `[lib] crate-type = ["cdylib", "rlib"]` so the introspector can link.

## Two-distribution opt-in (when native is optional)

When the Rust extension is an optional accelerator over a pure-Python fallback, ship two PyPI packages: a hatchling pure-Python parent and a maturin-built native sibling installed under the parent's namespace via `module-name = "<parent>._driver"`. Wire them with `[tool.uv.workspace]` for dev, gate runtime use behind `try: from <parent>._driver import ...` with a clear install hint on `ImportError`. See `django-cachex` for a working example: `crates/django-cachex-redis-rs/` plus `[tool.uv.workspace] members = ["crates/*"]` plus `pkgutil.extend_path` in the parent `__init__.py`.

---

Cross-references:
- `package-init` for maturin scaffolding, `Cargo.toml` skeleton, cibuildwheel, gitignore
- `general-python` for Python-side conventions
- `packages` for related tooling
