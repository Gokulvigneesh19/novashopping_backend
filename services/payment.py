import hashlib
import hmac
import logging
from decimal import Decimal

import razorpay
from django.conf import settings
from rest_framework import status

from core.exceptions import MessageError


logger = logging.getLogger(__name__)

CURRENCY = "INR"


def get_razorpay_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise MessageError(
            "Payment gateway is not configured.",
            status.HTTP_503_SERVICE_UNAVAILABLE
        )

    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def to_paise(amount):
    """Razorpay expects the smallest currency unit as an integer."""
    return int((Decimal(amount) * 100).quantize(Decimal("1")))


def create_razorpay_order(order):
    """Create the matching order on Razorpay and return its response dict."""
    client = get_razorpay_client()

    try:
        return client.order.create(
            data={
                "amount": to_paise(order.total_amount),
                "currency": CURRENCY,
                "receipt": order.order_number,
                "notes": {
                    "order_id": str(order.id),
                    "user_email": order.user.email,
                },
            }
        )
    except Exception:
        logger.exception("Razorpay order creation failed for %s", order.order_number)

        raise MessageError(
            "Could not start the payment. Please try again.",
            status.HTTP_502_BAD_GATEWAY
        )


def is_valid_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    """
    Check the signature Razorpay Checkout returns after a payment.

    Razorpay signs "<order_id>|<payment_id>" with the key secret (HMAC-SHA256),
    so only a real payment for this order can produce a matching signature.
    """
    get_razorpay_client()  # fails clearly if the keys aren't configured

    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, razorpay_signature or "")


def razorpay_checkout_options(order, payment):
    """Everything the frontend needs to open Razorpay Checkout for this order."""
    user = order.user

    return {
        "key_id": settings.RAZORPAY_KEY_ID,
        "order_id": payment.razorpay_order_id,
        "amount": to_paise(payment.amount),
        "currency": payment.currency,
        "name": "NovaShop",
        "description": f"Order {order.order_number}",
        "prefill": {
            "name": f"{user.first_name} {user.last_name}".strip(),
            "email": user.email,
            "contact": user.phone_number or order.shipping_phone_number,
        },
    }

