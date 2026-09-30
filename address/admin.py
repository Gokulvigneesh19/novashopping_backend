from django.contrib import admin
from models import Address


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "name",
        "address_type",
        "city",
        "state",
        "postal_code",
        "is_default",
        "created_at",
    )

    list_display_links = ("name",)

    search_fields = (
        "user__email",
        "name",
        "phone",
        "city",
        "postal_code",
    )

    list_filter = (
        "address_type",
        "is_default",
        "country",
    )

    ordering = ("user", "-is_default", "-created_at")
