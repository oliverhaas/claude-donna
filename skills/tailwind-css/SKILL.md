---
name: tailwind-css
description: "Tailwind CSS utility patterns, component composition, and Django integration. Use when writing Tailwind styles, configuring themes, or integrating Tailwind into a Django project."
user-invocable: false
---

# Tailwind CSS Patterns

## Utility Composition

Tailwind is verbose by design. Resist extracting utilities into custom classes prematurely. Use component templates or JS variables instead.

```html
<!-- Good: utilities inline -->
<button class="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:ring-offset-2">
  Save
</button>

<!-- Only extract when reused many times across files -->
```

When extraction is warranted, use `@apply` sparingly and only in component CSS, not in `base` or `utilities` layers:

```css
/* components.css */
@layer components {
  .btn-primary {
    @apply rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white;
    @apply hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:ring-offset-2;
  }
}
```

## Responsive Design

Tailwind is mobile-first. Unprefixed utilities apply at all sizes; prefixed ones apply at that breakpoint and above.

```html
<!-- Stack on mobile, row on md+ -->
<div class="flex flex-col md:flex-row">

<!-- Hide on mobile, show on lg+ -->
<div class="hidden lg:block">

<!-- Full width on mobile, fixed on sm+ -->
<div class="w-full sm:w-64">
```

Default breakpoints: `sm` 640px, `md` 768px, `lg` 1024px, `xl` 1280px, `2xl` 1536px.

Custom breakpoints in `tailwind.config.js`:

```javascript
theme: {
  screens: {
    'xs': '480px',
    // extend defaults
    ...require('tailwindcss/defaultTheme').screens,
  }
}
```

## Dark Mode

Configure mode in `tailwind.config.js`:

```javascript
// Class-based (recommended for user-controlled toggle)
darkMode: 'class',

// Media query (follows OS preference)
darkMode: 'media',
```

**Class-based toggle**: add/remove `dark` class on `<html>` or a parent element.

```javascript
// Toggle
document.documentElement.classList.toggle('dark')

// Persist preference
const isDark = localStorage.getItem('theme') === 'dark'
document.documentElement.classList.toggle('dark', isDark)
```

```html
<!-- Usage in templates -->
<div class="bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100">
  <p class="text-gray-600 dark:text-gray-400">Secondary text</p>
</div>
```

## Custom Theme Configuration

```javascript
// tailwind.config.js
const defaultTheme = require('tailwindcss/defaultTheme')

module.exports = {
  content: [
    './templates/**/*.html',
    './static/**/*.js',
    // Include Python files if you build class names there
    // './myapp/**/*.py',  -- only if safe (no dynamic class names)
  ],
  theme: {
    extend: {
      // Extend (add to) defaults
      colors: {
        brand: {
          50:  '#f0f9ff',
          500: '#0ea5e9',
          900: '#0c4a6e',
        },
      },
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans],
      },
      spacing: {
        '18': '4.5rem',
        '112': '28rem',
      },
    },
    // Replacing (not extending) defaults -- use sparingly
    // borderRadius: { DEFAULT: '0.25rem', lg: '0.5rem' }
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('daisyui'),
  ],
}
```

Never put full default config in your repo. Only include what you change.

## DaisyUI Component Patterns

DaisyUI adds semantic component classes on top of Tailwind utilities.

```html
<!-- Button variants -->
<button class="btn btn-primary">Primary</button>
<button class="btn btn-outline btn-sm">Small outline</button>
<button class="btn btn-ghost loading">Loading</button>

<!-- Card -->
<div class="card bg-base-100 shadow-md">
  <div class="card-body">
    <h2 class="card-title">Title</h2>
    <p>Content</p>
    <div class="card-actions justify-end">
      <button class="btn btn-primary">Action</button>
    </div>
  </div>
</div>

<!-- Alert -->
<div class="alert alert-warning">
  <span>Warning message</span>
</div>

<!-- Badge -->
<span class="badge badge-secondary badge-outline">Label</span>
```

DaisyUI themes override the full color palette. Configure in `tailwind.config.js`:

```javascript
daisyui: {
  themes: ['light', 'dark', 'corporate'],
  // or custom:
  themes: [
    {
      mytheme: {
        'primary': '#0ea5e9',
        'secondary': '#f000b8',
        'accent': '#1dcdbc',
        'neutral': '#2b3440',
        'base-100': '#ffffff',
      }
    },
    'dark',
  ],
  darkTheme: 'dark',
  logs: false,
}
```

Switch theme by setting `data-theme` on `<html>`:

```html
<html data-theme="corporate">
```

## CSS Specificity and Mixing with Existing Styles

When adding Tailwind to a project with existing CSS:

**Problem**: existing styles override Tailwind utilities due to specificity.

**Options (in order of preference):**

1. Use Tailwind's `!important` modifier (`!text-red-500` generates `!important`)
2. Scope legacy CSS under a class: `.legacy-scope { ... }` and only apply that class on old pages
3. Use CSS layers to control ordering:

```css
/* In your main CSS file, declare layer order */
@layer base, legacy, components, utilities;

/* Legacy styles go in a named layer so Tailwind utilities win */
@layer legacy {
  h1 { font-size: 2rem; }  /* Tailwind's utility layer beats this */
}

@tailwind base;
@tailwind components;
@tailwind utilities;
```

4. Increase specificity on problem elements with `:where()` / `:is()` or attribute selectors (last resort)

When inheriting a Bootstrap/Foundation project, consider running both in parallel during migration: Tailwind for new components, legacy framework for old ones, separated by template/component boundaries.

## Spacing, Typography, and Layout Reference

**Spacing scale** (1 unit = 4px): `p-1`=4px, `p-2`=8px, `p-4`=16px, `p-6`=24px, `p-8`=32px, `p-10`=40px, `p-12`=48px, `p-16`=64px.

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

**Typography:**

```html
<!-- prose: renders rich text (from @tailwindcss/typography) -->
<article class="prose prose-lg dark:prose-invert max-w-none">
  {{ content }}
</article>

<!-- Font sizes with leading -->
<p class="text-sm leading-relaxed">
<h1 class="text-3xl font-bold tracking-tight">
<span class="text-xs font-medium uppercase tracking-wide text-gray-500">
```

**Common text utilities:**
- `truncate` — single line ellipsis
- `line-clamp-3` — three-line clamp (requires `@tailwindcss/line-clamp` in Tailwind v3, built-in v3.3+)
- `break-words` — wrap long words
- `whitespace-pre-wrap` — preserve newlines

## Performance: Purging and Critical CSS

Tailwind removes unused CSS at build time via the `content` array in `tailwind.config.js`. This is mandatory for production.

**Key rules for safe purging:**

Do not build class names dynamically by string concatenation:

```javascript
// BAD: purge will not detect 'text-red-500' or 'text-green-500'
const cls = `text-${status}-500`

// GOOD: full class names present in source
const cls = status === 'error' ? 'text-red-500' : 'text-green-500'
```

For dynamic classes generated by Python/Django, use a safelist:

```javascript
// tailwind.config.js
safelist: [
  'text-red-500',
  'text-green-500',
  // or pattern:
  { pattern: /bg-(red|green|blue)-(100|500|900)/ },
],
```

**Build-time CSS generation** (with django-tailwind or direct CLI):

```bash
# Development (watch mode)
npx tailwindcss -i ./static/src/input.css -o ./static/css/styles.css --watch

# Production (minified)
npx tailwindcss -i ./static/src/input.css -o ./static/css/styles.css --minify
```

Critical CSS: for first-paint performance, inline the above-the-fold styles in `<head>`. Tools like `critical` or Vite's `vite-plugin-critical` can automate this. In most Django projects with HTMX/Alpine, this is not necessary unless running Lighthouse audits.

## Django Integration

### Option 1: django-tailwind (recommended for new projects)

```bash
pip install django-tailwind
# Optional: browser reload on template change
pip install django-browser-reload
```

```python
# settings.py
INSTALLED_APPS = [
    ...
    'tailwind',
    'theme',  # your theme app, generated below
    'django_browser_reload',  # optional
]

TAILWIND_APP_NAME = 'theme'
INTERNAL_IPS = ['127.0.0.1']
```

```bash
python manage.py tailwind init    # Creates 'theme' app
python manage.py tailwind install # npm install
python manage.py tailwind start   # Dev watch
python manage.py tailwind build   # Production build
```

The generated `theme/templates/base.html` includes the correct `{% tailwind_css %}` tag. In other templates:

```html
{% load tailwind_tags %}
<!DOCTYPE html>
<html>
<head>
  {% tailwind_css %}
</head>
```

### Option 2: Direct CLI in existing Django project

Add to `package.json` at project root:

```json
{
  "scripts": {
    "dev": "tailwindcss -i ./static/src/input.css -o ./static/css/tailwind.css --watch",
    "build": "tailwindcss -i ./static/src/input.css -o ./static/css/tailwind.css --minify"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.0",
    "@tailwindcss/forms": "^0.5.0",
    "@tailwindcss/typography": "^0.5.0"
  }
}
```

Static files config:

```python
# settings.py
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

In templates:

```html
{% load static %}
<link rel="stylesheet" href="{% static 'css/tailwind.css' %}">
```

### Static file pipeline for production

Commit the compiled `tailwind.css` to the repo, or generate it in CI before `collectstatic`. Do not rely on running the Tailwind CLI at runtime.

For Whitenoise:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    ...
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

Run in CI/deploy:

```bash
npm run build
python manage.py collectstatic --noinput
```

## Common Pitfalls

1. **Dynamic class names get purged**: always use full class names in source, or safelist patterns.
2. **`@apply` in `base` layer**: breaks the cascade. Only use `@apply` in `components` layer.
3. **DaisyUI theme conflicts with custom colors**: DaisyUI's semantic colors (`primary`, `secondary`) override your `extend.colors`. Use DaisyUI's theme system or rename your custom colors.
4. **Forgetting `dark:` variants on nested elements**: dark mode requires every element to declare its dark variant explicitly. There is no inheritance.
5. **Conflicting Tailwind + Bootstrap base styles**: both reset/normalize the browser. Only include one `base` layer or scope the other under a CSS layer.
6. **`content` array too narrow**: if Tailwind misses a file, classes in it are purged in production. Verify coverage with `--dry-run` or by checking the output CSS size.
