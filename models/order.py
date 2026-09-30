import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from .product import Product


class Order(models.Model):

    class Status(models.TextChoices):
        # pending -> confirmed -> packed -> in_transit -> delivered
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PACKED = "packed", "Packed"
        IN_TRANSIT = "in_transit", "In Transit"
        DELIVERED = "delivered", "Delivered"
        # Unpaid orders the customer cancelled, or paid orders that can't be fulfilled
        CANCELLED = "cancelled", "Cancelled"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "Cash on Delivery"
        ONLINE = "online", "Online Payment"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    order_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders"
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices
    )

    # Delivery address snapshot, copied from the chosen Address at checkout
    shipping_name = models.CharField(max_length=300)

    shipping_phone_code = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )

    shipping_phone_number = models.CharField(max_length=20)

    shipping_address = models.TextField()

    shipping_city = models.CharField(max_length=100)

    shipping_state = models.CharField(max_length=100)

    shipping_country = models.CharField(max_length=100)

    shipping_postal_code = models.CharField(
        max_length=20,
        blank=True,
        default=""
    )

    # Price breakdown
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    shipping_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    # Coupon snapshot: the code used and how much it took off
    coupon_code = models.CharField(
        max_length=50,
        blank=True,
        default=""
    )

    coupon_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    platform_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    # Optional notes from customer
    customer_note = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"

        super().save(*args, **kwargs)


class OrderItem(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items"
    )

    # Product snapshot, so later product edits don't change past orders
    product_name = models.CharField(max_length=200)

    product_image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True
    )

    # Pricing snapshot (mirrors Product.price / discount_percentage)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    quantity = models.PositiveIntegerField()

    # Discount amount for the whole line
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "orders"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.product_name} - {self.quantity}"

    @classmethod
    def from_product(cls, order, product, quantity):
        """Build an unsaved item that snapshots the product's current price."""
        unit_price_after_discount = product.price_after_discount.quantize(Decimal("0.01"))

        return cls(
            order=order,
            product=product,
            product_name=product.name,
            product_image=product.cover_image.name,
            unit_price=product.price,
            discount_percentage=product.discount_percentage,
            quantity=quantity,
            discount=(product.price - unit_price_after_discount) * quantity,
            total_price=unit_price_after_discount * quantity,
        )
