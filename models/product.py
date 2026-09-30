import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from .category import Category


class Product(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products"
    )

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products"
    )

    name = models.CharField(max_length=200)

    description = models.TextField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ]
    )


    @property
    def price_after_discount(self):
        return self.price - (
            self.price * self.discount_percentage / 100
        )

    stock = models.PositiveIntegerField(default=0)

    cover_image = models.ImageField(
        upload_to="products/"
    )
    
    is_active = models.BooleanField(default=True)

    is_bestseller = models.BooleanField(default=False)

    is_discounted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "products"

    def __str__(self):
        return self.name


class ProductImage(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="sub_images"
    )

    image = models.ImageField(upload_to="products/sub_images/")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "products"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.product.name} image"
