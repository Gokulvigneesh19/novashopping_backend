from django.urls import path

from views import ProductReviewsView, ReviewAndRatingView


urlpatterns = [
    path("", ReviewAndRatingView.as_view(), name="reviews"),
    path("product/<uuid:product_id>/", ProductReviewsView.as_view(), name="product-reviews"),
]
