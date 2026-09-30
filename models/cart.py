import uuid

from django.conf import settings
from django.db import models

from .coupon import Coupon
from .product import Product


class Cart(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        null=True,
        blank=True
    )

    session_key = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True
    )
    # Coupon applied through /api/cart/coupon/; used again at checkout
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        related_name="carts",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "cart"

    def __str__(self):
        if self.user:
            return f"Cart - {self.user.email}"
        return f"Cart - {self.session_key}"


class CartItem(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items"
    )

    quantity = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "cart"
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"],
                name="unique_cart_product"
            )
        ]

    def __str__(self):
        if self.cart.user:
            return f"{self.product.name} - {self.quantity} (User: {self.cart.user.email})"
        return f"{self.product.name} - {self.quantity} (Session: {self.cart.session_key})"
