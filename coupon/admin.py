from django.contrib import admin
from models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "discount_percentage",
        "active",
        "created_at",
        "updated_at",
    )

    list_display_links = ("code",)

    search_fields = ("code", "description")

    list_filter = ("active",)

    ordering = ("-created_at",)
