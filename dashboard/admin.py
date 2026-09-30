from django.contrib import admin
from models import DashboardSnapshot


@admin.register(DashboardSnapshot)
class DashboardSnapshotAdmin(admin.ModelAdmin):

    list_display = (
        "date",
        "total_revenue",
        "orders",
        "new_customers",
        "conversion_rate",
        "updated_at",
    )

    list_display_links = ("date",)

    date_hierarchy = "date"

    ordering = ("-date",)
