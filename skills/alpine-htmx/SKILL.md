---
name: alpine-htmx
description: "Alpine.js + HTMX integration patterns. Covers morph-based state preservation, event coordination, and swap pitfalls."
user-invocable: false
---

# Alpine.js + HTMX Integration

## The Core Problem

HTMX swaps replace DOM elements. Alpine state, event listeners, and component instances are destroyed unless you preserve them.

## Solution: alpine-morph

Use the alpine-morph extension so HTMX morphs the DOM instead of replacing it. Alpine state survives the swap.

```html
<div x-data="{ count: 0 }"
     hx-ext="alpine-morph"
     hx-swap="morph"
     hx-get="/api/counter">
  <span x-text="count"></span>
  <button @click="count++">+</button>
</div>
```

**Server must return the full element** (the div with x-data), not just a fragment.

## Event Coordination

HTMX fires DOM events that Alpine can listen to:

```html
<div x-data="{ loading: false }"
     @htmx:beforeRequest="loading = true"
     @htmx:afterSwap="loading = false">
  <span x-show="loading">Loading...</span>
  <button hx-get="/data" hx-target="#results">Load</button>
  <div id="results"></div>
</div>
```

Key HTMX events: `htmx:beforeRequest`, `htmx:afterSwap`, `htmx:afterSettle`, `htmx:responseError`

## Server-Triggered Events

Server sends custom events via `HX-Trigger` header. Alpine listens on window:

```python
# Django view
from django.http import JsonResponse
import json

def add_to_cart(request):
    # ... logic ...
    response = render(request, 'cart_item.html', ctx)
    response['HX-Trigger'] = json.dumps({
        'cart-updated': {'count': cart.item_count}
    })
    return response
```

```html
<div x-data="{ count: 0 }"
     @cart-updated.window="count = $event.detail.count">
  Cart: <span x-text="count"></span>
</div>
```

## Shared State via Alpine.store

Store persists even when components that read it are swapped:

```javascript
Alpine.store('cart', {
  items: [],
  add(item) { this.items.push(item) }
})
```

```html
<!-- This component can be HTMX-swapped without losing cart state -->
<div x-text="$store.cart.items.length"></div>
```

## Swap Targets: Keep Them Small

Don't swap the Alpine component itself when possible. Swap a child target instead:

```html
<!-- Good: Alpine component is stable, only results swap -->
<div x-data="{ query: '' }">
  <input x-model="query" name="q"
         hx-get="/search" hx-trigger="input changed delay:300ms"
         hx-target="#results">
  <div id="results"></div>
</div>
```

This avoids morph entirely. The x-model binding stays intact because the input is never swapped.

## Re-initialization Without Morph

If morph is not an option, manually re-init after swap:

```javascript
document.addEventListener('htmx:afterSettle', (e) => {
  Alpine.initTree(e.detail.target)
})
```

State is lost. Use only as fallback.

## Common Pitfalls

1. **State lost after swap**: Enable morph: `hx-ext="alpine-morph" hx-swap="morph"`. Server must return the full x-data element.
2. **x-model unbinds**: Either use morph, or don't swap the input's parent. Target a sibling container instead.
3. **Event listeners gone**: Without morph, all @click/@input handlers are lost on swap.
4. **Debounce conflict**: Don't debounce in both Alpine (x-model.debounce) and HTMX (hx-trigger delay). Pick one.
5. **x-data scope reset**: Each swap without morph creates a fresh scope. Use Alpine.store for state that must survive swaps.
