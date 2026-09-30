from django.contrib import admin
from models import Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    inlines = [ProductImageInline]

    list_display = (
        "id",
        "name",
        "category",
        "host",
        "price",
        "discount_percentage",
        "stock",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "description",
        "host__email",
    )

    list_filter = (
        "category",
        "is_active",
        "created_at",
    )

    ordering = ("-created_at",)

    list_display_links = ("name",)