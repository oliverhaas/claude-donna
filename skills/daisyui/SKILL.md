---
name: daisyui
description: DaisyUI v5 component patterns, semantic colors, design tokens, theming, and common compositions. Use when building UI with DaisyUI in Django/Jinja2 templates.
user-invocable: false
---

# DaisyUI v5

Component library on top of Tailwind CSS v4. Uses semantic class names instead of utility-only markup. See `tailwind-css` skill for Tailwind v4 setup and `@plugin "daisyui"` configuration.

## Color System

Use semantic color names, not Tailwind color utilities (`bg-primary` not `bg-blue-500`). Every color has a `-content` counterpart for foreground/text on that background.

| Color | Purpose | Content |
|-------|---------|---------|
| `primary` | Main brand, primary actions | `primary-content` |
| `secondary` | Secondary brand | `secondary-content` |
| `accent` | Accent/highlight | `accent-content` |
| `neutral` | Unsaturated dark UI elements | `neutral-content` |
| `base-100` | Page background | `base-content` |
| `base-200` | Slightly elevated surface | |
| `base-300` | More elevated surface | |
| `info` | Informational messages | `info-content` |
| `success` | Success/safe messages | `success-content` |
| `warning` | Caution messages | `warning-content` |
| `error` | Danger/destructive messages | `error-content` |

Components auto-pair colors with their `-content` variant. Opacity modifiers work: `text-base-content/50`.

## Design Tokens

Override these in a custom theme (`@plugin "daisyui/theme"`) to change the look globally.

| Variable | Controls | Applies to |
|----------|----------|------------|
| `--radius-box` | Border radius | Card, modal, alert, drawer |
| `--radius-field` | Border radius | Button, input, select, tab |
| `--radius-selector` | Border radius | Checkbox, toggle, badge, radio |
| `--size-field` | Base scale | Button, input, select |
| `--size-selector` | Base scale | Checkbox, toggle, radio |
| `--border` | Border width | All bordered components |
| `--depth` | Shadow/depth effects (0 or 1) | Card, button, dropdown |
| `--noise` | Background noise texture (0 or 1) | Page background |

## Component Modifier System

Three axes apply across most components. All modifiers are responsive (`md:btn-lg`, `lg:card-sm`).

**Style:** `-outline`, `-soft`, `-dash`, `-ghost`, `-link`
**Size:** `-xs`, `-sm`, `-md` (default), `-lg`, `-xl`
**Color:** `-primary`, `-secondary`, `-accent`, `-neutral`, `-info`, `-success`, `-warning`, `-error`

```html
<button class="btn btn-primary btn-soft btn-sm">Soft small primary</button>
<span class="badge badge-warning badge-dash badge-lg">Dashed large warning</span>
<div class="alert alert-info alert-soft">Soft info alert</div>
```

## Core Components

### Button

```html
<button class="btn">Default</button>
<button class="btn btn-primary">Primary</button>
<button class="btn btn-outline btn-secondary">Outlined</button>
<button class="btn btn-ghost">Ghost</button>
<button class="btn btn-link">Link</button>

<!-- Sizes -->
<button class="btn btn-xs">Tiny</button>
<button class="btn btn-xl">Extra large</button>

<!-- Shapes -->
<button class="btn btn-square">X</button>
<button class="btn btn-circle">+</button>
<button class="btn btn-wide">Wide</button>
<button class="btn btn-block">Full width</button>

<!-- States -->
<button class="btn btn-disabled" tabindex="-1" role="button">Disabled</button>
<button class="btn"><span class="loading loading-spinner"></span> Loading</button>
```

### Card

```html
<div class="card bg-base-100 shadow-sm">
  <figure><img src="..." alt=""></figure>
  <div class="card-body">
    <h2 class="card-title">Title</h2>
    <p>Description</p>
    <div class="card-actions justify-end">
      <button class="btn btn-primary">Action</button>
    </div>
  </div>
</div>

<!-- Compact card -->
<div class="card card-sm bg-base-100 shadow-sm">...</div>

<!-- Horizontal layout -->
<div class="card card-side bg-base-100 shadow-sm">
  <figure><img src="..." alt=""></figure>
  <div class="card-body">...</div>
</div>
```

### Modal (dialog-based)

```html
<button class="btn" onclick="my_modal.showModal()">Open</button>

<dialog id="my_modal" class="modal">
  <div class="modal-box">
    <form method="dialog">
      <button class="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">X</button>
    </form>
    <h3 class="text-lg font-bold">Title</h3>
    <p class="py-4">Content</p>
    <div class="modal-action">
      <form method="dialog">
        <button class="btn">Close</button>
      </form>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop">
    <button>close</button>
  </form>
</dialog>
```

Positioning: `modal-top`, `modal-bottom`, `modal-middle` (default). Responsive: `modal-bottom sm:modal-middle`.

### Dropdown (Popover API)

```html
<button class="btn" popovertarget="dd1" style="anchor-name:--dd1">
  Options
</button>
<ul class="dropdown menu w-52 rounded-box bg-base-100 shadow-sm"
    popover id="dd1" style="position-anchor:--dd1">
  <li><a>Item 1</a></li>
  <li><a>Item 2</a></li>
</ul>
```

Positioning: `dropdown-end`, `dropdown-top`, `dropdown-bottom`, `dropdown-left`, `dropdown-right`, `dropdown-center`.
Modifiers: `dropdown-hover`, `dropdown-open`.

### Alert & Toast

```html
<div class="alert alert-info">
  <span>Info message</span>
</div>

<div class="alert alert-error alert-soft">
  <span>Soft error</span>
</div>

<!-- Toast: fixed position container -->
<div class="toast toast-end">
  <div class="alert alert-success">
    <span>Saved.</span>
  </div>
</div>
```

Toast positions: `toast-start`, `toast-center`, `toast-end`, `toast-top`, `toast-middle`, `toast-bottom`. Combine: `toast toast-top toast-end`.

### Table

```html
<div class="overflow-x-auto">
  <table class="table">
    <thead>
      <tr><th>Name</th><th>Email</th><th>Role</th></tr>
    </thead>
    <tbody>
      <tr><td>Alice</td><td>alice@example.com</td><td>Admin</td></tr>
      <tr class="hover"><td>Bob</td><td>bob@example.com</td><td>User</td></tr>
    </tbody>
  </table>
</div>
```

Modifiers: `table-zebra`, `table-pin-rows`, `table-pin-cols`. Sizes: `table-xs`, `table-sm`, `table-md`, `table-lg`.

### Menu & Navbar

```html
<ul class="menu bg-base-200 rounded-box w-56">
  <li><a>Item 1</a></li>
  <li><a class="menu-active">Active</a></li>
  <li class="menu-disabled"><a>Disabled</a></li>
  <li>
    <details>
      <summary>Submenu</summary>
      <ul><li><a>Sub-item</a></li></ul>
    </details>
  </li>
</ul>

<div class="navbar bg-base-100">
  <div class="navbar-start"><a class="btn btn-ghost text-xl">Logo</a></div>
  <div class="navbar-center"><ul class="menu menu-horizontal px-1"><li><a>Link</a></li></ul></div>
  <div class="navbar-end"><button class="btn btn-primary">Action</button></div>
</div>
```

### Tabs

```html
<div role="tablist" class="tabs tabs-border">
  <a role="tab" class="tab">Tab 1</a>
  <a role="tab" class="tab tab-active">Tab 2</a>
  <a role="tab" class="tab">Tab 3</a>
</div>
```

Styles: `tabs-border` (underlined), `tabs-box` (boxed), `tabs-lift` (lifted). Sizes: `tabs-xs` through `tabs-xl`.

### Dock

Bottom navigation bar (replaces `btm-nav` from v4):

```html
<div class="dock">
  <button class="dock-active"><svg>...</svg><span class="dock-label">Home</span></button>
  <button><svg>...</svg><span class="dock-label">Search</span></button>
  <button><svg>...</svg><span class="dock-label">Settings</span></button>
</div>
```

### Drawer

```html
<div class="drawer lg:drawer-open">
  <input id="drawer" type="checkbox" class="drawer-toggle">
  <div class="drawer-content">
    <label for="drawer" class="btn btn-ghost drawer-button lg:hidden">Menu</label>
    <!-- page content -->
  </div>
  <div class="drawer-side">
    <label for="drawer" aria-label="close sidebar" class="drawer-overlay"></label>
    <ul class="menu bg-base-200 min-h-full w-80 p-4">
      <li><a>Sidebar item</a></li>
    </ul>
  </div>
</div>
```

`lg:drawer-open` keeps the sidebar permanently visible on large screens.

### Steps

```html
<ul class="steps">
  <li class="step step-primary">Register</li>
  <li class="step step-primary">Payment</li>
  <li class="step">Confirm</li>
</ul>
```

`steps-vertical` for vertical layout.

### Form Inputs

```html
<fieldset class="fieldset">
  <legend class="fieldset-legend">Account</legend>

  <label class="label">Email</label>
  <input type="email" class="input" placeholder="you@example.com">

  <label class="label">Password</label>
  <input type="password" class="input">

  <label class="label">Role</label>
  <select class="select">
    <option>Admin</option>
    <option>User</option>
  </select>

  <label class="label">Bio</label>
  <textarea class="textarea" placeholder="About you"></textarea>

  <label class="label cursor-pointer">
    <span>Remember me</span>
    <input type="checkbox" class="checkbox">
  </label>
</fieldset>
```

Input modifiers: `input-primary`, `input-error`, etc. Sizes: `input-xs` through `input-xl`. Same pattern for `select`, `textarea`, `checkbox`, `toggle`, `radio`.

### Validator

Changes input colors based on HTML validation state:

```html
<input type="email" class="input validator" required placeholder="Email">
<p class="validator-hint">Please enter a valid email</p>
```

`validator-hint` is hidden until the field is invalid and touched.

### Filter

Group of radio buttons for filtering:

```html
<div class="filter">
  <input class="filter-reset" type="radio" name="status" aria-label="All">
  <input class="btn filter-btn" type="radio" name="status" aria-label="Active">
  <input class="btn filter-btn" type="radio" name="status" aria-label="Inactive">
</div>
```

## Theming

35 built-in themes: light, dark, cupcake, bumblebee, emerald, corporate, synthwave, retro, cyberpunk, valentine, halloween, garden, forest, aqua, lofi, pastel, fantasy, wireframe, black, luxury, dracula, cmyk, autumn, business, acid, lemonade, night, coffee, winter, dim, nord, sunset, caramellatte, abyss, silk.

```css
@plugin "daisyui" {
  themes: light --default, dark --prefersdark, corporate;
}
```

`--default` sets the page default. `--prefersdark` activates for `prefers-color-scheme: dark`. Use `all` to enable all 35.

Apply via `data-theme` on any element (themes nest):

```html
<html data-theme="corporate">
  <div data-theme="dark"><!-- this section uses dark theme --></div>
</html>
```

### Custom theme

```css
@plugin "daisyui/theme" {
  name: "myapp";
  default: true;
  color-scheme: light;
  --color-primary: oklch(0.55 0.22 240);
  --color-secondary: oklch(0.65 0.18 320);
  --color-accent: oklch(0.70 0.20 160);
  --color-neutral: oklch(0.30 0.02 240);
  --color-base-100: oklch(0.98 0.005 240);
  --color-base-200: oklch(0.94 0.008 240);
  --color-base-300: oklch(0.90 0.010 240);
  --radius-box: 1rem;
  --radius-field: 0.5rem;
  --radius-selector: 0.25rem;
  --depth: 1;
  --noise: 0;
}
```

## Common Compositions

### Navbar + Drawer layout

```html
<div class="drawer lg:drawer-open">
  <input id="drawer" type="checkbox" class="drawer-toggle">
  <div class="drawer-content">
    <div class="navbar bg-base-100 lg:hidden">
      <label for="drawer" class="btn btn-ghost">Menu</label>
      <span class="text-xl font-bold">App</span>
    </div>
    <main class="p-6">{% block content %}{% endblock %}</main>
  </div>
  <div class="drawer-side">
    <label for="drawer" class="drawer-overlay"></label>
    <ul class="menu bg-base-200 min-h-full w-64 p-4">
      <li><a href="{% url 'dashboard' %}">Dashboard</a></li>
      <li><a href="{% url 'settings' %}">Settings</a></li>
    </ul>
  </div>
</div>
```

### Card grid

```html
<div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
  {% for item in items %}
  <div class="card bg-base-100 shadow-sm">
    <div class="card-body">
      <h2 class="card-title">{{ item.name }}</h2>
      <p>{{ item.description }}</p>
      <div class="card-actions justify-end">
        <a href="{{ item.get_absolute_url }}" class="btn btn-primary btn-sm">View</a>
      </div>
    </div>
  </div>
  {% endfor %}
</div>
```

### Form with validation

```html
<form method="post" action="{% url 'create' %}">
  {% csrf_token %}
  <fieldset class="fieldset w-full max-w-md">
    <legend class="fieldset-legend">New Item</legend>

    <label class="label">Name</label>
    <input type="text" name="name" class="input validator w-full" required
           minlength="3" value="{{ form.name.value|default:'' }}">
    <p class="validator-hint">At least 3 characters</p>

    <label class="label">Category</label>
    <select name="category" class="select w-full">
      {% for c in categories %}
      <option value="{{ c.pk }}">{{ c.name }}</option>
      {% endfor %}
    </select>

    <div class="mt-4">
      <button type="submit" class="btn btn-primary">Create</button>
    </div>
  </fieldset>
</form>
```

## Migration from v4

| v4 class | v5 class |
|----------|----------|
| `btm-nav` | `dock` |
| `btm-nav-label` | `dock-label` |
| `card-compact` | `card-sm` |
| `online` (avatar) | `avatar-online` |
| `offline` (avatar) | `avatar-offline` |
| `placeholder` (avatar) | `avatar-placeholder` |
| `disabled` (menu) | `menu-disabled` |
| `active` (menu) | `menu-active` |
| `focus` (menu) | `menu-focus` |
| `btn-group` | `join` |
| `input-group` | `join` |
| `form-control` | `fieldset` |

Removed: `artboard`, `mask-parallelogram-*`.

Theme variables renamed: `--p` -> `--color-primary`, `--b1` -> `--color-base-100`, `--rounded-box` -> `--radius-box`, `--rounded-btn` -> `--radius-field`, `--rounded-badge` -> `--radius-selector`, `--border-btn` -> `--border`.
