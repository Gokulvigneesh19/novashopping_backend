from django.urls import path

from views import (
    CheckoutView,
    OrderCancelView,
    OrderPayView,
    OrderView,
    PaymentFailedView,
    VerifyPaymentView,
)


urlpatterns = [
    path("", OrderView.as_view(), name="orders"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("verify-payment/", VerifyPaymentView.as_view(), name="verify-payment"),
    path("payment-failed/", PaymentFailedView.as_view(), name="payment-failed"),
    path("<uuid:order_id>/", OrderView.as_view(), name="order-detail"),
    path("<uuid:order_id>/pay/", OrderPayView.as_view(), name="order-pay"),
    path("<uuid:order_id>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
]
