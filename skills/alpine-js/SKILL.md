---
name: alpine-js
description: "Core Alpine.js patterns, reactivity model, and common pitfalls."
user-invocable: false
---

# Alpine.js Patterns

## Data & Components

```html
<!-- Inline -->
<div x-data="{ open: false, toggle() { this.open = !this.open } }">

<!-- Reusable via Alpine.data -->
<div x-data="dropdown">
```

```javascript
Alpine.data('dropdown', () => ({
  open: false,
  toggle() { this.open = !this.open },
  close() { this.open = false }
}))
```

**Alpine.store** for global state (toasts, theme, user). **Alpine.data** for reusable component-local logic.

```javascript
Alpine.store('notifications', {
  items: [],
  add(msg) { this.items.push(msg) }
})
// Access: $store.notifications.items
```

## Binding & Events

```html
<input x-model="search">
<input x-model.debounce-500="query">   <!-- 500ms debounce -->
<input x-model.lazy="name">            <!-- on blur only -->
<input x-model.number="count">

<button @click="open = !open">Toggle</button>
<div @click.away="close()">            <!-- click outside -->
<div @scroll.window.throttle-200="onScroll">
```

Modifiers: `.prevent`, `.stop`, `.window`, `.document`, `.debounce-N`, `.throttle-N`, `.away`

## Watching & Effects

**x-effect** -- eager, auto-tracks dependencies, runs immediately:
```html
<span x-effect="doubled = count * 2"></span>
```

**$watch** -- lazy, fires only on change, gives old/new values:
```javascript
init() {
  this.$watch('search', (val, old) => this.fetchResults(val))
}
```

Do not modify watched data inside x-effect -- infinite loop.

## DOM

```html
<div x-show="open">              <!-- CSS display toggle (fast) -->
<template x-if="open">           <!-- DOM insert/remove (use for heavy content) -->
<template x-for="item in items" :key="item.id">

<input x-ref="searchBox">
<button @click="$refs.searchBox.focus()">
```

x-show for frequent toggles. x-if for rare/heavy content. $refs only works on static DOM (not inside x-for).

## Async

```javascript
init() {
  fetch('/api/items').then(r => r.json()).then(d => this.items = d)
}

// $nextTick: wait for DOM update
this.items.push(newItem)
await this.$nextTick()
const height = this.$el.scrollHeight
```

## Custom Events

```javascript
// Dispatch
$dispatch('item-added', { id: 123 })

// Listen (same component tree)
<div @item-added="handle($event.detail)">

// Listen (cross-component, via window)
<div @item-added.window="handle($event.detail)">
```

## Reactivity Gotchas

Alpine uses JavaScript Proxy for reactivity. Key rules:

**Nested object changes -- reassign the parent:**
```javascript
// Won't always trigger update
this.user.name = 'Alice'

// Reliable
this.user = { ...this.user, name: 'Alice' }
```

**Array mutations that work:**
```javascript
this.items.push(item)          // works
this.items.splice(0, 1)       // works
this.items = this.items.filter(i => i.active)  // works
```

**Non-reactive data** -- store outside x-data scope:
```javascript
const LOOKUP = Object.freeze(largeConfig)  // outside Alpine

Alpine.data('myComponent', () => ({
  get config() { return LOOKUP }
}))
```

## Common Mistakes

1. x-model only works with native inputs (input, select, textarea) -- not custom components
2. $refs on x-for items -- use computed properties or $el instead
3. x-effect that writes to its own dependencies -- causes infinite loop
4. Forgetting `:key` on x-for -- causes stale DOM and binding issues
5. Using x-data properties for cross-component state -- use Alpine.store instead
