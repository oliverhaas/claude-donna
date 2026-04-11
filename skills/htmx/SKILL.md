---
name: htmx
description: "HTMX 4.0 core attributes, swap strategies, triggers, OOB swaps, SSE, morph swaps, and Django partial view patterns. Targets htmx 4.0 (currently alpha, stable expected early 2027). Use when building hypermedia-driven pages with server-rendered HTML."
user-invocable: false
---

# HTMX 4.0 Patterns

htmx 4.0 is a significant rewrite. Key internals changed: fetch() replaces XMLHttpRequest, attribute inheritance is now explicit, history uses network requests instead of DOM snapshots, and several extension features (morph swaps, SSE) moved into core.

## Core Attributes

These are unchanged from 2.x:

```html
hx-get="/endpoint"
hx-post="/endpoint"
hx-put="/endpoint"
hx-delete="/endpoint"
hx-patch="/endpoint"

<!-- Where to put the response -->
hx-target="#results"           <!-- CSS selector -->
hx-target="closest tr"        <!-- relative selector -->
hx-target="next .error"       <!-- next sibling matching selector -->
hx-target="this"              <!-- the element itself -->

<!-- How to put the response -->
hx-swap="innerHTML"           <!-- default: replace inner content -->
hx-swap="outerHTML"           <!-- replace the entire element -->
hx-swap="beforeend"           <!-- append inside, at the end -->
hx-swap="afterend"            <!-- insert after the element -->
hx-swap="delete"              <!-- remove the target, ignore response -->
hx-swap="none"                <!-- process response headers only -->
hx-swap="morphInner"          <!-- NEW in 4.0 core: idiomorph inner swap -->
hx-swap="morphOuter"          <!-- NEW in 4.0 core: idiomorph outer swap -->

<!-- Include additional form values -->
hx-include="#extra-form"
hx-vals='{"key": "value"}'
```

`morphInner` and `morphOuter` were previously only available via the `idiomorph` extension. In 4.0 they are built-in core swap options. Prefer morph swaps when the swapped content has child elements with local state (Alpine, focus, scroll position).

## Swap Modifiers

Same as 2.x, appended to `hx-swap` with a space:

```html
hx-swap="innerHTML swap:500ms"           <!-- delay before swap -->
hx-swap="innerHTML settle:200ms"         <!-- delay before removing old classes -->
hx-swap="innerHTML transition:true"      <!-- use View Transitions API -->
hx-swap="innerHTML scroll:top"           <!-- scroll target to top after swap -->
hx-swap="innerHTML show:top"            <!-- show top of target after swap -->
hx-swap="beforeend scroll:bottom"       <!-- append + scroll to bottom (chat) -->
```

View Transitions queue sequentially in 4.0 — transitions complete before the next one starts, eliminating cancellation artifacts from rapid requests.

## Triggers

Same as 2.x:

```html
hx-trigger="click"                       <!-- default for buttons/links -->
hx-trigger="change"                      <!-- default for inputs -->
hx-trigger="submit"                      <!-- default for forms -->
hx-trigger="load"                        <!-- fire on page load -->
hx-trigger="revealed"                    <!-- fire when scrolled into view -->
hx-trigger="intersect"                   <!-- fire on intersection observer -->
hx-trigger="every 5s"                    <!-- polling -->
hx-trigger="input changed delay:300ms"  <!-- debounced input -->
hx-trigger="keyup[key=='Enter']"         <!-- conditional filter -->
hx-trigger="click from:#other-btn"      <!-- trigger from another element -->
hx-trigger="custom-event from:window"   <!-- custom DOM event -->
```

Trigger modifiers: `once`, `changed`, `delay:Nms`, `throttle:Nms`, `from:<selector>`, `target:<selector>`, `consume`, `queue:first|last|all|none`.

## Attribute Inheritance (Breaking Change)

In 2.x, attributes like `hx-target` and `hx-swap` inherited from ancestors implicitly (CSS-like). In 4.0, inheritance is opt-in using the `:inherited` modifier:

```html
<!-- 4.0: explicit inheritance required -->
<div hx-target:inherited="#results" hx-swap:inherited="outerHTML">
  <button hx-get="/a">A</button>
  <button hx-get="/b">B</button>
</div>
```

Without `:inherited`, child elements do not pick up parent attributes. To restore 2.x behavior globally:

```javascript
htmx.config.attributeInheritance = "implicit"
```

Prefer explicit inheritance in new code.

## Event Names (Breaking Change)

Event names changed from camelCase to a structured format:

```
htmx:<phase>:<system>[:<sub-action>]
```

| htmx 2.x | htmx 4.0 |
|---|---|
| `htmx:beforeRequest` | `htmx:before:request` |
| `htmx:afterRequest` | `htmx:after:request` |
| `htmx:beforeSwap` | `htmx:before:swap` |
| `htmx:afterSwap` | `htmx:after:swap` |
| `htmx:beforeSettle` | `htmx:before:settle` |
| `htmx:afterSettle` | `htmx:after:settle` |
| `htmx:load` | `htmx:after:load` |
| `htmx:historyRestore` | `htmx:after:history:restore` |

Update all `addEventListener` and `hx-on` calls when migrating.

## hx-on Scripting (Breaking Change)

4.0 standardizes on a single `hx-on:<event-name>` syntax. Previous variants are removed.

```html
<!-- 4.0 syntax — only this form is supported -->
<button hx-get="/data"
        hx-on:htmx:before:request="this.disabled = true"
        hx-on:htmx:after:settle="this.disabled = false">
  Load
</button>
```

4.0 also supports async handlers via a `ctx` object:

```html
<form hx-post="/submit"
      hx-on:htmx:before:request="await ctx.beforeSubmit(event)">
```

The `ctx` object provides access to request/response context in async handlers.

## Response Code Handling (Breaking Change)

In 2.x, HTMX skipped 4xx and 5xx responses by default (swap did not happen). In 4.0, only deliberate `204` (No Content) and `304` (Not Modified) are ignored. All other responses — including 4xx and 5xx — are processed and swapped normally.

This means:

- You no longer need to return 422 for validation errors. Return 400 or 422; the body will be swapped.
- 500 errors will also be swapped. Make sure error pages are safe to render inline.
- `204` still suppresses the swap (useful for delete operations that fire `HX-Trigger`).

```python
# 4.0: 400 works fine for validation errors
def create_item(request):
    form = ItemForm(request.POST)
    if not form.is_valid():
        return render(request, "partials/item_form.html", {"form": form}, status=400)
    # ...
```

To opt back into 2.x error-skipping behavior, configure `responseHandling`:

```javascript
htmx.config.responseHandling = [
  {code: "204", swap: false},
  {code: "304", swap: false},
  {code: "[23]..", swap: true},
  {code: "[45]..", swap: false, error: true},  // 2.x behavior
]
```

## Out-of-Band (OOB) Swaps (Simplified)

4.0 reverts OOB to simple id-based outerHTML replacement. The complex positional variants (`beforeend`, `prepend`, `append`) on `hx-swap-oob` are removed. Use `<htmx-partial>` for more control (see below).

```html
<!-- Server response -->
<div id="main-content">...primary content...</div>

<!-- OOB: replaces the element with matching id in the DOM (outerHTML) -->
<div id="notification-count" hx-swap-oob="true">3</div>
```

`hx-swap-oob="true"` means outerHTML replacement. That is the only supported OOB form in 4.0.

For innerHTML-only OOB or append/prepend patterns, use `<htmx-partial>` instead.

## htmx-partial Tag (New in 4.0)

A new template-based element for OOB partial content with full `hx-target`/`hx-swap` support:

```html
<!-- In server response body -->
<htmx-partial hx-target="#notification-count" hx-swap="innerHTML">
  3
</htmx-partial>

<htmx-partial hx-target="#activity-log" hx-swap="beforeend">
  <li>Item created at 14:32</li>
</htmx-partial>
```

`<htmx-partial>` elements are never rendered themselves — they act as instructions to swap their content into `hx-target`. This replaces the use of `hx-swap-oob` with custom swap strategies.

## History Handling (Breaking Change)

4.0 removes DOM snapshots from local/session storage. History navigation triggers a network request to restore content instead.

```html
hx-push-url="true"              <!-- push hx-get/post URL to history -->
hx-push-url="/explicit/path"    <!-- push a specific URL -->
hx-replace-url="true"
hx-replace-url="/explicit/path"
```

There is no `historyCacheSize` config in 4.0. Pages must handle navigation re-requests server-side (always render the current state).

History caching can be re-enabled via the opt-in history cache extension if needed:

```html
<script src="https://unpkg.com/htmx-ext-history-cache"></script>
<body hx-ext="history-cache">
```

## SSE (Reintegrated into Core)

SSE no longer requires the `htmx-ext-sse` extension. New syntax in 4.0:

```html
<div hx-sse="/events">
  <div hx-sse-swap="message"></div>
</div>
```

Named events:

```html
<div hx-sse="/events">
  <div hx-sse-swap="status-update" hx-target="#status" hx-swap="outerHTML"></div>
  <div hx-sse-swap="notification" hx-target="#notifs" hx-swap="beforeend"></div>
</div>
```

Django SSE view (unchanged pattern, but works with regular views now — SSE no longer forces async):

```python
import time
from django.http import StreamingHttpResponse

def event_stream(request):
    def generator():
        while True:
            data = get_latest_data()
            yield f"event: status-update\ndata: {data}\n\n"
            time.sleep(2)
    return StreamingHttpResponse(generator(), content_type="text/event-stream")
```

Use `CONN_MAX_AGE=0` or a separate async view to avoid holding a DB connection during streaming.

## Streaming Responses (New in 4.0)

fetch() enables native streaming via readable streams. HTMX 4.0 can progressively render streamed HTML:

```html
<div hx-get="/stream" hx-swap="beforeend" hx-trigger="load">
  <!-- content appended as chunks arrive -->
</div>
```

Django async streaming view:

```python
from django.http import StreamingHttpResponse

async def stream_view(request):
    async def generator():
        async for chunk in generate_chunks():
            yield f"<p>{chunk}</p>"
    return StreamingHttpResponse(generator(), content_type="text/html")
```

## WebSocket Extension

Still requires `htmx-ext-ws` (unchanged):

```html
<div hx-ext="ws" ws-connect="/ws/chat/">
  <div id="chat-messages"></div>
  <form ws-send>
    <input name="message">
    <button type="submit">Send</button>
  </form>
</div>
```

## Optimistic Updates Extension (New in 4.0)

Optimistic updates are now a bundled core extension:

```html
<button hx-post="/like"
        hx-ext="optimistic"
        hx-optimistic-target="#like-count"
        hx-optimistic-swap="innerHTML"
        hx-optimistic-value="<span>42</span>">
  Like
</button>
```

The target is updated immediately with `hx-optimistic-value`, then replaced with the server response when it arrives. If the request fails, the original content is restored.

## Headers

### Sent by HTMX (request headers)

```
HX-Request: true
HX-Boosted: true
HX-Current-URL: /current/page
HX-Prompt: <user input>
HX-Target: target-element-id
HX-Trigger: triggering-element-id
HX-Trigger-Name: triggering-element-name
```

### Sent by server (response headers)

```
HX-Location: /new-url            -- client-side redirect (no reload)
HX-Push-Url: /new-url            -- push URL to browser history
HX-Replace-Url: /new-url         -- replace URL (no new entry)
HX-Redirect: /url                -- full page redirect
HX-Refresh: true                 -- force full page refresh
HX-Retarget: #different-target  -- override hx-target from server
HX-Reswap: outerHTML             -- override hx-swap from server
HX-Trigger: event-name           -- fire event after settle
HX-Trigger-After-Swap: event     -- fire event after swap
HX-Trigger-After-Settle: event   -- fire event after settle
```

For `HX-Trigger` with data:
```
HX-Trigger: {"cart-updated": {"count": 3}}
```

### 286 Status Code

Return HTTP 286 to stop polling on an `every Ns` trigger without swapping.

## Loading States

```html
<!-- HTMX adds htmx-request class to the issuing element -->
<style>
  button.htmx-request { opacity: 0.5; pointer-events: none; }
</style>

<!-- hx-indicator: show a spinner during request -->
<button hx-get="/data" hx-indicator="#spinner">Load</button>
<img id="spinner" class="htmx-indicator" src="/spinner.gif">

<!-- Disable element during request -->
hx-disabled-elt="this"
hx-disabled-elt="#submit-btn"
```

## Forms and Validation Feedback

```html
<form hx-post="/submit" hx-target="#form-errors" hx-swap="innerHTML">
  <input name="email" type="email">
  <div id="form-errors"></div>
  <button type="submit">Submit</button>
</form>
```

Inline validation:

```html
<input name="email" type="email"
       hx-post="/validate/email"
       hx-trigger="blur"
       hx-target="next .error"
       hx-swap="outerHTML">
<span class="error"></span>
```

In 4.0, the server can return 400 directly — no need for 422 to force swap.

## Boost

```html
<body hx-boost="true">
<a href="/download" hx-boost="false">Download</a>
```

Boosted links/forms request with fetch(), swap `<body>` innerHTML, push the URL. `hx-boost` does not send `HX-Target`/`HX-Trigger`; check only `HX-Request` and `HX-Boosted`.

## Django View Patterns

### Detect HTMX requests

```python
def my_view(request):
    if request.headers.get("HX-Request"):
        return render(request, "partials/results.html", context)
    return render(request, "results.html", context)
```

### Response headers helper

```python
from django.http import HttpResponse

def update_item(request, pk):
    item = get_object_or_404(Item, pk=pk)
    # ... update logic ...
    response = render(request, "partials/item_row.html", {"item": item})
    response["HX-Trigger"] = "item-updated"
    response["HX-Push-Url"] = f"/items/{item.pk}/"
    return response
```

### 204 for no-content swaps

204 still suppresses swapping in 4.0. Use for deletes that only fire a trigger:

```python
def delete_item(request, pk):
    Item.objects.filter(pk=pk).delete()
    return HttpResponse(status=204, headers={"HX-Trigger": "item-deleted"})
```

### Partial templates

```html
<!-- templates/partials/item_row.html -->
<tr id="item-{{ item.pk }}">
  <td>{{ item.name }}</td>
  <td>
    <button hx-delete="/items/{{ item.pk }}/"
            hx-target="closest tr"
            hx-swap="outerHTML swap:300ms">Delete</button>
  </td>
</tr>
```

```html
<!-- templates/items.html -->
{% for item in items %}
  {% include "partials/item_row.html" %}
{% endfor %}
```

### Validation errors

In 4.0, error status codes are swapped by default. Return 400:

```python
def create_item(request):
    form = ItemForm(request.POST)
    if not form.is_valid():
        return render(request, "partials/item_form.html", {"form": form}, status=400)
    # ...
```

## Configuration

```javascript
htmx.config.defaultSwapStyle = "innerHTML"
htmx.config.defaultSettleDelay = 20
htmx.config.includeIndicatorStyles = true
htmx.config.withCredentials = false
htmx.config.timeout = 0

// Attribute inheritance: "explicit" (default in 4.0) or "implicit" (2.x behavior)
htmx.config.attributeInheritance = "explicit"

// Response handling: 204 and 304 suppressed, everything else swapped (4.0 default)
htmx.config.responseHandling = [
  {code: "204", swap: false},
  {code: "304", swap: false},
  {code: ".*", swap: true},
]
```

Note: `historyCacheSize` and `refreshOnHistoryMiss` are removed in 4.0. History uses network requests.

## Common Pitfalls

1. **Attribute inheritance**: In 4.0, `hx-target` and `hx-swap` on a parent do not propagate to children without `:inherited`. Add it or set `htmx.config.attributeInheritance = "implicit"`.
2. **Event name mismatch**: `htmx:beforeRequest` no longer fires. Update all listeners and `hx-on` to the new `htmx:before:request` format.
3. **OOB without matching ID**: `hx-swap-oob="true"` elements must match an existing `id` in the DOM or are silently dropped.
4. **History re-request not handled**: Since 4.0 restores history via network, views used with `hx-push-url` must render correctly when re-fetched at any time.
5. **500 responses now swap**: Make sure server error responses render safely as partials.
6. **SSE old extension syntax**: Remove `hx-ext="sse"` and `sse-connect`/`sse-swap`. Use `hx-sse` and `hx-sse-swap` (built-in).
7. **Polling throttled in hidden tabs**: Use SSE for reliable updates.
8. **Forms inside swap target**: If the form is inside `hx-target`, the swap replaces the form. Target a sibling container instead.

## Alpine.js Integration

See `donna:alpine-htmx` for Alpine + HTMX state preservation, morph-based swaps, and event coordination patterns.
