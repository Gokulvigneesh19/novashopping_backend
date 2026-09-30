from django.urls import include, path


# Mounted at /api/ by shopping_backend/urls.py
urlpatterns = [
    path("", include("urls.user")),
    path("categories/", include("urls.category")),
    path("products/", include("urls.product")),
    path("cart/", include("urls.cart")),
    path("wishlist/", include("urls.wishlist")),
    path("reviews/", include("urls.review")),
    path("addresses/", include("urls.address")),
    path("orders/", include("urls.order")),
    path("coupons/", include("urls.coupon")),
    path("admin/", include("urls.admin")),
]
