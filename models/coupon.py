import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Coupon(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    code = models.CharField(
        max_length=50,
        unique=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    # A coupon gives EITHER a percentage off OR a flat amount off (the other stays 0)
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ]
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    # Order subtotal needed before the code can be used (0 = no minimum)
    min_order_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )

    # When the code starts working; defaults to the moment it's created
    start_date = models.DateTimeField(default=timezone.now)

    # When the code stops working; empty = never expires
    end_date = models.DateTimeField(
        blank=True,
        null=True
    )

    # Only usable by customers who haven't completed (paid for) an order yet
    only_for_new = models.BooleanField(default=False)

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "coupon"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gt=models.F("start_date")),
                name="coupon_end_after_start"
            )
        ]

    def __str__(self):
        return self.code

    @classmethod
    def live(cls):
        """Coupons that are active and inside their date range right now."""
        now = timezone.now()

        return cls.objects.filter(
            active=True,
            start_date__lte=now
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gt=now)
        )

    @property
    def is_live(self):
        now = timezone.now()

        return (
            self.active
            and self.start_date <= now
            and (self.end_date is None or self.end_date > now)
        )

    def is_applicable(self, order_amount):
        """True if the code can be used on an order with this subtotal."""
        return self.is_live and order_amount >= self.min_order_amount

    def discount_for(self, amount):
        """How much this coupon takes off `amount` (never more than the amount itself)."""
        if self.discount_percentage > 0:
            discount = (amount * self.discount_percentage / 100).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )
        else:
            discount = self.discount_amount

        return min(discount, amount)