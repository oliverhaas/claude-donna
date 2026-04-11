---
name: tailwind-css
description: "Tailwind CSS v4 utility patterns, component composition, and Django integration. Targets Tailwind v4 (CSS-first config, @theme directive, no tailwind.config.js). Use when writing Tailwind styles, configuring themes, or integrating Tailwind v4 into a Django project."
user-invocable: false
---

# Tailwind CSS v4 Patterns

Targets Tailwind CSS v4 (released January 2025, latest v4.2). The config-file era is over: everything lives in CSS via the `@theme` directive.

## Installation

```bash
# Vite project (preferred)
npm install -D tailwindcss @tailwindcss/vite

# Standalone CLI
npm install -D tailwindcss @tailwindcss/cli

# PostCSS
npm install -D tailwindcss @tailwindcss/postcss
```

Vite plugin (`vite.config.js`):

```javascript
import tailwindcss from '@tailwindcss/vite'

export default {
  plugins: [tailwindcss()],
}
```

## CSS Entry Point

Replace all `@tailwind` directives with a single import. There is no `tailwind.config.js`.

```css
/* main.css */
@import "tailwindcss";

/* Optional: explicit source paths (auto-detection covers most cases) */
@source "../templates/**/*.html";
@source "../myapp/**/*.py";

/* All customization goes in @theme */
@theme {
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-display: "Satoshi", "sans-serif";

  --color-brand-50:  oklch(0.97 0.02 240);
  --color-brand-500: oklch(0.55 0.22 240);
  --color-brand-900: oklch(0.25 0.12 240);

  --breakpoint-xs: 480px;
  --breakpoint-3xl: 1920px;

  --spacing-18: 4.5rem;
  --spacing-112: 28rem;
}
```

Colors use oklch by default in v4 — more vivid on modern displays and easier to manipulate programmatically. All theme values are exposed as CSS custom properties at runtime.

## Auto-Detection and @source

Tailwind v4 scans for class names automatically, respecting `.gitignore`. You only need `@source` for:

- Paths outside your project root
- Files listed in `.gitignore` that you still want scanned
- Python files where class names are built from full strings

```css
/* Only add @source when auto-detection misses something */
@source "../vendor/my-lib/templates/**/*.html";
```

Do not build class names by concatenation — auto-detection requires full class names in source:

```python
# BAD: scanner cannot see 'text-red-500' or 'text-green-500'
cls = f"text-{status}-500"

# GOOD: full names visible to scanner
cls = "text-red-500" if status == "error" else "text-green-500"
```

For truly dynamic classes from Python, use `@source` with `not-pattern` or add them to a safelist via CSS:

```css
@source inline("text-red-500 text-green-500 text-yellow-500 bg-red-100 bg-green-100");
```

## Utility Composition

Tailwind is verbose by design. Resist extracting utilities prematurely. Use component templates or JS variables to share markup.

When extraction is warranted, `@apply` still works in `@layer components`:

```css
@layer components {
  .btn-primary {
    @apply rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white;
    @apply hover:bg-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2;
  }
}
```

Do not use `@apply` in `@layer base` or `@layer utilities` — this breaks the cascade. `@layer components` only.

v4 uses native CSS cascade layers: `@layer theme, base, components, utilities`. Tailwind declares these automatically; you can insert your own layers at specific positions.

## New Utility Features in v4

**Dynamic values** — arbitrary steps work without configuration:

```html
<div class="grid-cols-15 mt-17 w-29 gap-13">
```

**Gradient rename** — `bg-gradient-*` is now `bg-linear-*`:

```html
<!-- v4 -->
<div class="bg-linear-to-r from-brand-500 to-purple-600">
<div class="bg-radial-[at_top_left] from-white to-brand-500">
<div class="bg-conic from-blue-500 via-purple-500 to-blue-500">
```

**3D transforms**:

```html
<div class="transform-3d rotate-x-12 rotate-y-6 perspective-500">
```

**New shadow compositing**:

```html
<div class="shadow-lg inset-shadow-sm ring-1 inset-ring-brand-500/20">
```

**Auto-resize textarea**:

```html
<textarea class="field-sizing-content min-h-20 w-full resize-none">
```

**`not-*` variant** — negate pseudo-classes and media queries:

```html
<li class="not-last:border-b border-gray-200">
<div class="not-dark:bg-white dark:bg-gray-900">
```

**`starting` variant** — `@starting-style` for enter animations:

```html
<dialog class="open:opacity-100 starting:open:opacity-0 transition-opacity">
```

**Logical property utilities** (v4.2):

```html
<!-- block-start / block-end / inline-start / inline-end -->
<div class="pbs-4 pbe-6 mbs-2 mbe-4">
```

## Container Queries

Built-in — no plugin needed:

```html
<div class="@container">
  <div class="@sm:flex-row flex flex-col">
  <div class="@max-md:hidden">  <!-- max-width container query -->
  <div class="@[600px]:grid-cols-3">  <!-- arbitrary container size -->
</div>
```

## Responsive Design

Mobile-first. Unprefixed utilities apply at all sizes; prefixed ones at that breakpoint and above.

```html
<!-- Stack on mobile, row on md+ -->
<div class="flex flex-col md:flex-row">

<!-- Hide on mobile, show on lg+ -->
<div class="hidden lg:block">

<!-- Full width on mobile, fixed on sm+ -->
<div class="w-full sm:w-64">
```

Default breakpoints: `sm` 640px, `md` 768px, `lg` 1024px, `xl` 1280px, `2xl` 1536px.

Custom breakpoints via `@theme` (not `tailwind.config.js`):

```css
@theme {
  --breakpoint-xs: 480px;
  --breakpoint-3xl: 1920px;
  /* Removing a default breakpoint: */
  --breakpoint-2xl: initial;
}
```

## Dark Mode

Dark mode works via the `dark:` variant. In v4, the strategy is configured in CSS:

```css
@import "tailwindcss";

/* Class-based dark mode (user-controlled toggle) */
@variant dark (&:where(.dark, .dark *));

/* Media-based dark mode (default if no @variant override) */
/* @variant dark (@media (prefers-color-scheme: dark)); */
```

Toggle class-based dark mode:

```javascript
document.documentElement.classList.toggle('dark')

// Persist preference
const isDark = localStorage.getItem('theme') === 'dark'
document.documentElement.classList.toggle('dark', isDark)
```

Usage in templates:

```html
<div class="bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100">
  <p class="text-gray-600 dark:text-gray-400">Secondary text</p>
</div>
```

Every element must declare its own `dark:` variant — there is no inheritance.

## DaisyUI v5

Install: `npm install -D daisyui@5`. Add `@plugin "daisyui"` to your CSS entry point after `@import "tailwindcss"`. See the `daisyui` skill for component patterns, theming, design tokens, and Django template compositions.

## CSS Specificity and Mixing with Existing Styles

v4 uses native CSS cascade layers, which gives you precise control when adding Tailwind to an existing project.

```css
@import "tailwindcss";

/* Declare additional layers; utilities layer always wins over lower layers */
@layer legacy {
  h1 { font-size: 2rem; }  /* Tailwind utilities beat this automatically */
}
```

Options when existing styles win over utilities:

1. Use `!` modifier (`!text-red-500` generates `!important`)
2. Scope legacy CSS in its own `@layer` so utilities take precedence
3. Scope legacy CSS under a `.legacy-scope` class and only apply to old pages
4. Last resort: raise specificity with `:is()` / `:where()` selectors

When inheriting a Bootstrap project, run both in parallel: Tailwind for new components, Bootstrap for old ones, separated by template/component boundaries.

## Spacing, Typography, and Layout Reference

**Spacing scale** (1 unit = 4px): `p-1`=4px, `p-2`=8px, `p-4`=16px, `p-6`=24px, `p-8`=32px, `p-10`=40px, `p-12`=48px, `p-16`=64px. Arbitrary steps like `p-17` or `p-29` work without configuration in v4.

**Common layout patterns:**

```html
<!-- Centered container -->
<div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">

<!-- Two-column with sidebar -->
<div class="grid grid-cols-1 gap-8 lg:grid-cols-[280px_1fr]">

<!-- Flexbox row, wrap, centered -->
<div class="flex flex-wrap items-center justify-between gap-4">

<!-- Sticky header -->
<header class="sticky top-0 z-10 bg-white shadow">

<!-- Full-height layout -->
<body class="flex min-h-screen flex-col">
  <main class="flex-1">
```

**Typography** (`@tailwindcss/typography` still a separate plugin in v4):

```html
<article class="prose prose-lg dark:prose-invert max-w-none">
  {{ content }}
</article>

<h1 class="text-3xl font-bold tracking-tight">
<p class="text-sm leading-relaxed">
<span class="text-xs font-medium uppercase tracking-wide text-gray-500">
```

**Common text utilities:**
- `truncate` — single-line ellipsis
- `line-clamp-3` — three-line clamp (built-in since v3.3, still works in v4)
- `break-words` — wrap long words
- `whitespace-pre-wrap` — preserve newlines

## Django Integration

### Option 1: Direct CLI (recommended for v4)

`django-tailwind` does not support Tailwind v4 yet (as of early 2026). Use the CLI directly.

```bash
npm install -D tailwindcss @tailwindcss/cli
```

`package.json` at project root:

```json
{
  "scripts": {
    "dev": "tailwindcss -i ./static/src/input.css -o ./static/css/tailwind.css --watch",
    "build": "tailwindcss -i ./static/src/input.css -o ./static/css/tailwind.css --minify"
  },
  "devDependencies": {
    "tailwindcss": "^4.0.0",
    "@tailwindcss/cli": "^4.0.0"
  }
}
```

`static/src/input.css`:

```css
@import "tailwindcss";

/* Explicit source paths for Django templates */
@source "../../templates/**/*.html";
@source "../../**/templates/**/*.html";

@theme {
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --color-brand-500: oklch(0.55 0.22 240);
}
```

Django settings:

```python
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

Template:

```html
{% load static %}
<link rel="stylesheet" href="{% static 'css/tailwind.css' %}">
```

### Option 2: Vite + django-vite

For projects already using Vite (`django-vite` package):

```javascript
// vite.config.js
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [tailwindcss()],
  build: {
    outDir: 'static/dist',
    rollupOptions: {
      input: 'static/src/main.css',
    },
  },
})
```

### Production Pipeline

Commit compiled `tailwind.css` to repo, or generate in CI before `collectstatic`. Never run the CLI at runtime.

CI / deploy:

```bash
npm run build
python manage.py collectstatic --noinput
```

For Whitenoise:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    ...
]
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

## Common Pitfalls

1. **Dynamic class names get missed by scanner**: always write full class names in source, or use `@source inline(...)` to safelist them.
2. **Using `tailwind.config.js`**: this is v3 syntax. In v4 all config is in CSS via `@theme`. Delete it.
3. **`@tailwind base/components/utilities` directives**: remove them. Replace with `@import "tailwindcss"`.
4. **`@apply` outside `@layer components`**: only use `@apply` inside `@layer components`. It breaks the cascade in other layers.
5. **`bg-gradient-to-r` in v4**: the class is now `bg-linear-to-r`. Rename all gradient utilities.
6. **`darkMode: 'class'` config**: this was `tailwind.config.js` syntax. In v4, configure dark mode via `@variant dark` in CSS.
7. **DaisyUI v4 + Tailwind v4**: incompatible. You need DaisyUI v5 (see `daisyui` skill).
8. **`django-tailwind`**: does not support Tailwind v4 as of early 2026. Use the CLI or Vite directly.
9. **Not scoping `@source` on multi-app Django projects**: auto-detection works from the directory where you run the CLI. Add explicit `@source` paths for apps in non-standard locations.

## Cross-references

- Alpine.js reactive state and Tailwind class toggling: see `donna:alpine-js` skill
- Alpine + HTMX patterns including class transitions: see `donna:alpine-htmx` skill
