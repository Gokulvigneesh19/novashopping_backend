from django.urls import path

from views import CouponView


urlpatterns = [
    path("", CouponView.as_view(), name="coupons"),
    path("<uuid:coupon_id>/", CouponView.as_view(), name="coupon-detail"),
]
