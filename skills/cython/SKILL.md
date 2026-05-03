---
name: cython
description: "Cython 3 authoring patterns and footguns. Use when writing or reviewing .pyx/.pxd code, pure-Python-mode extension types, free-threading support, or Cython-specific build configuration."
user-invocable: false
---

# Cython

Authoring guide for Cython 3 extensions. For scaffolding a new package with a Cython extension (build backend, cibuildwheel, gitignore), see `package-init`.

## `cdef` returning a C numeric type silently swallows exceptions

Cython 3 made the default exception mode `noexcept` for `cdef`/`cpdef` functions returning C numeric types. Without an `except` clause, a Python exception raised inside is printed to stderr and execution continues with an undefined return value.

Pick the clause that fits the return type:

```cython
cdef int find(...) except -1:        # -1 is impossible as a valid return
cdef int score(...) except? -1:      # -1 IS a valid return; the ? makes it ambiguous-checked
cdef double f(...) except *:         # any return value valid; always-correct, slightly slower
cdef object g(...):                  # Python-object returns propagate exceptions natively
```

In pure-Python mode the same rule applies via `@cython.exceptval(-1)` or `@cython.exceptval(check=True)` decorators on `@cython.cfunc` / `@cython.ccall` definitions.

## Pure-Python mode is the default; `.pyx` is for C interop

Stick to `.py` files with `import cython` and decorators (`@cython.cclass`, `@cython.ccall`, `@cython.cfunc`, `cython.declare`). The file stays valid Python, ruff/mypy/pytest keep working, and you get a fallback path when Cython isn't installed:

```python
try:
    import cython
except ImportError:

    class _CythonStub:
        bint = bool

        @staticmethod
        def cclass(klass): return klass
        @staticmethod
        def cfunc(fn): return fn
        @staticmethod
        def ccall(fn): return fn
        @staticmethod
        def inline(fn): return fn

    cython = _CythonStub()
```

Reach for `.pyx` only when you need `cdef extern from`, typed memoryviews with `nogil` blocks, fused types, `cimport` of `.pxd`, or `# distutils: language=c++`.

## Pure-mode `cclass` constraints (the real footguns)

These trip people up because the compiler errors are unhelpful or silent:

- **`@cython.cclass` cannot inherit from a regular Python class.** A regular Python class subclassing a cclass is fine. So `Variable` (never subclassed externally) can be a cclass; `Node` (subclassed by third-party tag libraries) must stay a regular class.
- **`@cython.ccall` / `cpdef` methods cannot accept `*args` or `**kwargs`.** Keep variadic methods as `def`.
- **`@cython.ccall` only works on `@cython.cclass` methods or module-level functions.** On a regular Python class method it crashes the compiler with a misleading `AttributeError`.
- **Drop `__slots__` when adding `@cython.cclass`.** The C struct replaces it.
- **No `match`/`case`.** Cython doesn't parse PEP 634; rewrite to `if`/`elif` chains.

## Memoryviews, not `cnp.ndarray`

For numeric buffers, use typed memoryviews. They're lightweight, slice without the GIL, and don't need `cnp.import_array()` boilerplate:

```cython
cdef double sum_2d(double[:, ::1] arr):   # ::1 marks C-contiguous; required for vectorization
    ...
```

`double[::1, :]` is Fortran-contiguous, `double[:, :]` is strided fallback (slower). If you ever see the strided form in a hot path, that's the optimization target.

## `nogil` declares; `with nogil:` releases

`cdef func() nogil:` declares that `func` is safe to call without holding the GIL; the caller is responsible for releasing it first. The release primitive is the `with nogil:` block:

```cython
with nogil:
    for i in range(n):
        result += compute(i)        # compute must be cdef ... nogil
```

Do not assume marking a function `nogil` releases the GIL on entry. It doesn't.

## Free-threading marker

Per-module, top of the file:

```cython
# cython: freethreading_compatible=True
```

Or set it once in `cythonize(compiler_directives={"freethreading_compatible": True})` for the whole package. Without it, importing the extension under cp314t re-enables the GIL and prints a `RuntimeWarning`.

## `cython -a` is the optimization tool

Run `cython -a path/to/file.py` (or `.pyx`) to get an HTML annotation. Yellow lines are Python interactions (slow); white lines compiled to pure C. In a hot path, every yellow line is a candidate for typing or refactoring. Annotate when you actually want speed, not as a default; aggressive directives without measuring is cargo-cult and `boundscheck=False` will reward you with a segfault when the bounds *are* wrong.

## Editable installs do not auto-rebuild

`uv sync` and `pip install -e .` with setuptools do not pick up `.py`/`.pyx` changes. You re-run `uv pip install -e .` after every edit. `meson-python` is the alternative if auto-rebuild matters, but it's a different build backend; switching is a project-level decision, not a per-file fix.

A `.pxd` change does correctly invalidate the dependent `.py`/`.pyx` files on next rebuild.

---

Cross-references:
- `package-init` for build backend, `cythonize()` setup, cibuildwheel, gitignore
- `general-python` for Python-side conventions
- `packages` for related tooling
