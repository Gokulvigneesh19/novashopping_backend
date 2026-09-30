from django.contrib import admin
from models import Cart, CartItem


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cart_owner",
        "session_key",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "user__email",
        "session_key",
    )

    ordering = ("-created_at",)

    list_display_links = ("id",)

    @admin.display(description="Owner")
    def cart_owner(self, obj):
        if obj.user:
            return obj.user.email

        return "Guest"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cart",
        "product",
        "quantity",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "cart__user__email",
        "cart__session_key",
        "product__name",
    )

    ordering = ("-created_at",)

    list_display_links = ("id",)

