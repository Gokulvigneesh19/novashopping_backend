import uuid

from django.db import models


class DashboardSnapshot(models.Model):
    """One day's dashboard stats, saved so past days don't have to be recomputed from orders."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    date = models.DateField(unique=True)

    # Paid, not-cancelled orders placed that day
    total_revenue = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    # Orders whose payment went through (paid or later refunded)
    orders = models.PositiveIntegerField(default=0)

    # Customers whose first paid order was that day
    new_customers = models.PositiveIntegerField(default=0)

    # Orders created that day, paid or not (the conversion rate's denominator)
    checkouts = models.PositiveIntegerField(default=0)

    # Paid orders / checkouts started, as a percentage
    conversion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "dashboard"
        ordering = ["-date"]

    def __str__(self):
        return f"Dashboard {self.date}"
