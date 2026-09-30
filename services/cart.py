from django.db import transaction

from rest_framework import status

from core.exceptions import MessageError
from models import Cart, Coupon, OrderItem

from .order import calculate_totals, get_coupon_error


def get_request_cart(request):
    """Return the logged-in user's cart or the guest session's cart, or None."""
    if request.user.is_authenticated:
        return Cart.objects.filter(
            user=request.user
        ).first()

    session_key = request.session.session_key

    if not session_key:
        return None

    return Cart.objects.filter(
        session_key=session_key,
        user__isnull=True
    ).first()


def get_or_create_request_cart(request):
    """Like get_request_cart, but creates the cart (and guest session) if needed."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(
            user=request.user
        )
        return cart

    if not request.session.session_key:
        request.session.create()

    cart, _ = Cart.objects.get_or_create(
        session_key=request.session.session_key,
        user=None
    )
    return cart


@transaction.atomic
def merge_guest_cart(session_key, user):

    if not session_key:
        return

    guest_cart = Cart.objects.filter(
        session_key=session_key,
        user=None
    ).first()

    if not guest_cart:
        return

    user_cart, _ = Cart.objects.get_or_create(
        user=user
    )

    # Keep the coupon the guest applied, unless the user's cart already has one
    if guest_cart.coupon_id and not user_cart.coupon_id:
        user_cart.coupon_id = guest_cart.coupon_id
        user_cart.save(update_fields=["coupon", "updated_at"])

    for guest_item in guest_cart.items.all():

        user_item = user_cart.items.filter(
            product=guest_item.product
        ).first()

        if user_item:
            user_item.quantity += guest_item.quantity
            user_item.save(
                update_fields=["quantity"]
            )
        else:
            guest_item.cart = user_cart
            guest_item.save(
                update_fields=["cart"]
            )

    guest_cart.delete()


def get_cart_totals(items, coupon=None, user=None):
    """
    Price breakdown for cart items, calculated exactly like checkout
    so the cart shows the same amount the customer will pay.
    """
    order_items = [
        OrderItem.from_product(None, item.product, item.quantity)
        for item in items
    ]

    totals = calculate_totals(order_items, coupon, user)

    coupon_info = None
    if coupon:
        error = get_coupon_error(coupon, totals["subtotal"] - totals["discount"], user)
        coupon_info = {
            "code": coupon.code,
            "discount_percentage": str(coupon.discount_percentage),
            "discount_amount": str(coupon.discount_amount),
            "min_order_amount": str(coupon.min_order_amount),
            "only_for_new": coupon.only_for_new,
            # False when the coupon expired or the cart dropped below the minimum
            "is_applied": error is None,
            "message": error,
        }

    return {
        "total_items": sum(item.quantity for item in items),
        # Strings, like every other price in the API
        "subtotal": str(totals["subtotal"]),
        "discount": str(totals["discount"]),
        "coupon": coupon_info,
        "coupon_discount": str(totals["coupon_discount"]),
        "cart_amount": str(totals["total_amount"]),
    }


def apply_coupon(cart, code):
    """Check `code` against the cart and save it on the cart, or raise with the reason."""
    code = (code or "").strip().upper()

    if not code:
        raise MessageError("Please enter a coupon code.")

    coupon = Coupon.objects.filter(code=code).first()

    if not coupon:
        raise MessageError("Invalid coupon code.", status.HTTP_404_NOT_FOUND)

    items = list(cart.items.select_related("product")) if cart else []

    if not items:
        raise MessageError("Your cart is empty.")

    totals = calculate_totals([
        OrderItem.from_product(None, item.product, item.quantity)
        for item in items
    ])
    error = get_coupon_error(coupon, totals["total_amount"], cart.user)

    if error:
        raise MessageError(error)

    cart.coupon = coupon
    cart.save(update_fields=["coupon", "updated_at"])

    return cart, items


def remove_coupon(cart):
    if cart and cart.coupon_id:
        cart.coupon = None
        cart.save(update_fields=["coupon", "updated_at"])

