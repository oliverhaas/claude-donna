---
name: django-admin
description: Django admin patterns for ModelAdmin, inlines, custom actions, custom views, permissions, and performance. Use when writing or customizing Django admin classes.
user-invocable: false
---

# Django Admin Patterns

Practical patterns for building maintainable, performant Django admin interfaces.

## ModelAdmin: list_display, list_filter, search, ordering

```python
from django.contrib import admin
from django.utils.html import format_html
from .models import Order

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "customer_link", "status", "total", "created_at"]
    list_filter = ["status", "created_at", ("merchant", admin.RelatedOnlyFieldListFilter)]
    search_fields = ["id", "customer__email", "customer__name"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    def customer_link(self, obj):
        url = reverse("admin:accounts_customer_change", args=[obj.customer_id])
        return format_html('<a href="{}">{}</a>', url, obj.customer)
    customer_link.short_description = "Customer"
    customer_link.admin_order_field = "customer__name"
```

**list_filter tips:**
- Use `admin.RelatedOnlyFieldListFilter` to filter FK dropdowns to values that actually appear in the list — prevents overly long filter sidebars on large datasets.
- Use `SimpleListFilter` for computed or multi-field filters.

```python
class ActiveMerchantFilter(admin.SimpleListFilter):
    title = "merchant status"
    parameter_name = "merchant_active"

    def lookups(self, request, model_admin):
        return [("yes", "Active"), ("no", "Inactive")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(merchant__is_active=True)
        if self.value() == "no":
            return queryset.filter(merchant__is_active=False)
        return queryset
```

## Readonly Fields and Conditional Display

```python
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ["created_at", "updated_at", "total_display"]

    def get_readonly_fields(self, request, obj=None):
        # Lock fields after submission
        if obj and obj.status != Order.Status.DRAFT:
            return self.readonly_fields + ["customer", "merchant"]
        return self.readonly_fields

    def total_display(self, obj):
        return f"{obj.total} {obj.currency}"
    total_display.short_description = "Total"
```

`get_readonly_fields(request, obj=None)` is the right hook — `obj` is `None` for add forms, an instance for change forms. Use this for state-dependent locking.

## Inlines: Tabular vs Stacked, Limits

```python
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0          # Don't show blank rows by default
    max_num = 50       # Cap total allowed rows
    show_change_link = True
    fields = ["product", "quantity", "unit_price", "line_total"]
    readonly_fields = ["line_total"]

    def line_total(self, obj):
        return obj.quantity * obj.unit_price
    line_total.short_description = "Total"


class OrderNoteInline(admin.StackedInline):
    model = OrderNote
    extra = 1
    fields = ["text", "created_by"]
    readonly_fields = ["created_by"]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline, OrderNoteInline]
```

**Tabular** — compact, good for many rows with few fields.
**Stacked** — verbose, good for few rows with many fields.

Always set `extra = 0` in production — blank rows confuse users and generate empty validation errors on save.

For nested inlines (inline inside inline), Django doesn't support this natively. Use `django-nested-admin` if needed, but prefer flatter models.

## Custom Actions (Bulk and Single-Object)

```python
from django.contrib import messages
from django.utils.translation import ngettext


@admin.action(description="Mark selected orders as shipped")
def mark_shipped(modeladmin, request, queryset):
    updated = queryset.filter(status=Order.Status.PAID).update(
        status=Order.Status.SHIPPED
    )
    modeladmin.message_user(
        request,
        ngettext(
            "%d order marked as shipped.",
            "%d orders marked as shipped.",
            updated,
        ) % updated,
        messages.SUCCESS,
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    actions = [mark_shipped]
```

**Single-object action** via a custom change-form button is better done as a custom view (see below) or a dedicated URL in `change_view`. For simple single-object transitions, add a method that renders a button via `readonly_fields` and handle the POST in a custom URL.

**Guarding actions:**
```python
@admin.action(description="Refund selected orders")
def refund_orders(modeladmin, request, queryset):
    if not request.user.has_perm("orders.can_refund"):
        modeladmin.message_user(request, "Permission denied.", messages.ERROR)
        return
    for order in queryset:
        OrderService.refund(order=order, user=request.user)
```

## Custom Admin Views and URLs

Add custom views to a `ModelAdmin` by overriding `get_urls()`:

```python
from django.urls import path
from django.shortcuts import get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    change_form_template = "admin/orders/order/change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:pk>/refund/",
                self.admin_site.admin_view(self.refund_view),
                name="orders_order_refund",
            ),
        ]
        return custom_urls + urls

    def refund_view(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        if request.method == "POST":
            OrderService.refund(order=order, user=request.user)
            self.message_user(request, "Order refunded.", messages.SUCCESS)
            return redirect(
                reverse("admin:orders_order_change", args=[pk])
            )
        # GET: render a confirmation page
        context = {
            **self.admin_site.each_context(request),
            "order": order,
            "opts": self.model._meta,
            "title": f"Refund order {order.id}",
        }
        return render(request, "admin/orders/order/refund_confirm.html", context)
```

Always use `self.admin_site.admin_view(...)` — it enforces login and `is_staff` checks. Add the button to the template:

```html
{# templates/admin/orders/order/change_form.html #}
{% extends "admin/change_form.html" %}
{% block object-tools-items %}
    {{ block.super }}
    {% if original %}
    <li>
        <a href="{% url 'admin:orders_order_refund' original.pk %}" class="button">
            Refund
        </a>
    </li>
    {% endif %}
{% endblock %}
```

## Admin Template Overriding

Django resolves admin templates in this order:
1. `templates/admin/<app_label>/<model_name>/<template>.html`
2. `templates/admin/<app_label>/<template>.html`
3. `templates/admin/<template>.html`
4. Django's built-in admin templates

Override the minimum needed — extend the parent template and fill specific blocks:

```html
{# templates/admin/orders/order/change_list.html #}
{% extends "admin/change_list.html" %}

{% block content_title %}
    <h1>Orders — {{ cl.result_count }} result{{ cl.result_count|pluralize }}</h1>
{% endblock %}

{% block object-tools-items %}
    {{ block.super }}
    <li><a href="{% url 'admin:orders_order_export' %}" class="button">Export CSV</a></li>
{% endblock %}
```

Useful blocks: `content_title`, `object-tools-items`, `submit_row`, `field_sets`, `after_related_objects`.

For global admin changes (header, branding), override `templates/admin/base_site.html`:

```html
{% extends "admin/base.html" %}
{% block branding %}<h1 id="site-name">My App Admin</h1>{% endblock %}
```

## Admin Permissions Patterns

```python
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True  # Allow list view
        return request.user.is_superuser or obj.merchant == request.user.merchant

    def has_delete_permission(self, request, obj=None):
        return False  # Never delete orders through admin

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Scope to the user's own merchant
        return qs.filter(merchant=request.user.merchant)
```

Override `get_queryset()` in combination with `has_*_permission()` to scope both the list and form views. `get_queryset()` alone is sufficient to prevent list access, but permission methods are needed to block direct URL access.

## Performance: get_queryset, select_related, prefetch

The admin calls `get_queryset()` for every list view. Override it to add prefetches that match `list_display`:

```python
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "customer_email", "merchant_name", "item_count", "status"]
    list_select_related = ["customer", "merchant"]  # Simple FK joins on list view

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related("items")
        qs = qs.annotate(item_count_annotation=Count("items"))
        return qs

    def customer_email(self, obj):
        return obj.customer.email  # No extra query: list_select_related
    customer_email.admin_order_field = "customer__email"

    def merchant_name(self, obj):
        return obj.merchant.name  # No extra query: list_select_related
    merchant_name.admin_order_field = "merchant__name"

    def item_count(self, obj):
        return obj.item_count_annotation
    item_count.short_description = "Items"
    item_count.admin_order_field = "item_count_annotation"
```

**`list_select_related`** — set to a list of FK field names for the list view only. Setting it to `True` does an unbounded `select_related()` — avoid that.

**`show_full_result_count = False`** — disable the expensive `COUNT(*)` on the full unfiltered table when the list is filtered. Default is `True`.

```python
class OrderAdmin(admin.ModelAdmin):
    show_full_result_count = False
```

## Admin Site Customization

### Subclass AdminSite for branding/title

```python
# admin_site.py
from django.contrib.admin import AdminSite

class MyAdminSite(AdminSite):
    site_header = "My App Administration"
    site_title = "My App"
    index_title = "Dashboard"


admin_site = MyAdminSite(name="myadmin")
```

```python
# apps.py
from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from .admin_site import admin_site
        # Re-register everything or use the custom site directly in each app
```

Use `@admin_site.register(Model)` or `admin_site.register(Model, ModelAdmin)` instead of `admin.register`.

### Multiple Admin Sites

Two independent admin sites — e.g., one for staff and one for a client-facing support portal:

```python
# admin_site.py
from django.contrib.admin import AdminSite

class StaffAdminSite(AdminSite):
    site_header = "Staff Portal"

class SupportAdminSite(AdminSite):
    site_header = "Support Portal"

staff_admin = StaffAdminSite(name="staff_admin")
support_admin = SupportAdminSite(name="support_admin")
```

```python
# urls.py
from .admin_site import staff_admin, support_admin

urlpatterns = [
    path("staff/", staff_admin.urls),
    path("support/", support_admin.urls),
]
```

Register models to each site explicitly. Models on the default `django.contrib.admin.site` are invisible to custom sites.

## Summary

- `extra = 0` on all inlines in production
- `list_select_related` with explicit field list, never `True`
- Override `get_queryset()` to add annotations and prefetches that match `list_display`
- `show_full_result_count = False` for large tables
- Use `self.admin_site.admin_view()` to wrap custom view functions
- Scope access in both `get_queryset()` and `has_*_permission()` — one without the other is incomplete
- `get_readonly_fields(request, obj=None)` for state-dependent locking; `obj` is `None` on add
- Override admin templates at the narrowest scope (`app/model/template.html` before `app/template.html`)

---
