from django.urls import path

from views import CartCountView, CartCouponView, CartView


urlpatterns = [
    path("", CartView.as_view(), name="cart"),
    path("count/", CartCountView.as_view(), name="cart-count"),
    path("coupon/", CartCouponView.as_view(), name="cart-coupon"),
    path("<uuid:item_id>/", CartView.as_view(), name="cart-item"),
]
