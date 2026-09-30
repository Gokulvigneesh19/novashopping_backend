from django.contrib import admin
from models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        "product",
        "product_name",
        "unit_price",
        "discount_percentage",
        "quantity",
        "discount",
        "tax",
        "total_price",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    inlines = [OrderItemInline]

    list_display = (
        "order_number",
        "user",
        "status",
        "payment_status",
        "payment_method",
        "total_amount",
        "created_at",
    )

    list_display_links = ("order_number",)

    search_fields = (
        "order_number",
        "user__email",
    )

    list_filter = (
        "status",
        "payment_status",
        "payment_method",
        "created_at",
    )

    readonly_fields = (
        "order_number",
        "subtotal",
        "discount",
        "total_amount",
    )

    ordering = ("-created_at",)
