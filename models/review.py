import uuid

from django.conf import settings
from django.db import models


class ReviewAndRating(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE
    )
    rating = models.PositiveIntegerField()
    review = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "reviewsandratings"

    def __str__(self):
        return f"{self.user} - {self.product} - {self.rating}"
