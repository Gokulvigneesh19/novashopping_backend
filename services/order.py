import logging
from decimal import Decimal

from django.db import transaction
from rest_framework import status

from core.exceptions import MessageError
from models import Cart, CartItem, Order, OrderItem, Payment, Product

from .payment import CURRENCY, create_razorpay_order, is_valid_signature


logger = logging.getLogger(__name__)


# Flat charges added to every order; change here when pricing rules are decided
SHIPPING_FEE = Decimal("0.00")
TAX = Decimal("0.00")
PLATFORM_FEE = Decimal("0.00")


def validate_cart(user):
    """Return (cart, cart_items, locked products by id), or raise if the cart can't be ordered."""
    cart = Cart.objects.select_related("coupon").filter(user=user).first()
    cart_items = list(cart.items.select_related("product")) if cart else []

    if not cart_items:
        raise MessageError("Your cart is empty.")

    # Lock the product rows so stock can't change while the order is created
    products = Product.objects.select_for_update().in_bulk(
        [item.product_id for item in cart_items]
    )

    errors = []

    for item in cart_items:
        product = products[item.product_id]

        if not product.is_active:
            errors.append({
                "product_id": product.id,
                "product_name": product.name,
                "message": "This product is no longer available.",
            })
        elif item.quantity > product.stock:
            errors.append({
                "product_id": product.id,
                "product_name": product.name,
                "message": "Requested quantity is greater than available stock.",
                "requested_quantity": item.quantity,
                "available_stock": product.stock,
            })

    if errors:
        raise MessageError(
            "Some items in your cart can't be ordered.",
            errors=errors
        )

    return cart, cart_items, products


def is_new_customer(user):
    """A customer is new until they have a paid order (abandoned or failed checkouts don't count)."""
    return not Order.objects.filter(
        user=user,
        payment_status=Order.PaymentStatus.PAID
    ).exists()


def get_coupon_error(coupon, amount, user=None):
    """Why `coupon` can't be used on `amount` (after product discounts), or None if it can."""
    if not coupon.is_live:
        return "This coupon has expired or is not active."

    if coupon.only_for_new:
        if user is None or not user.is_authenticated:
            return "Please log in to use this coupon."

        if not is_new_customer(user):
            return "This coupon is only valid on your first order."

    if amount < coupon.min_order_amount:
        return f"Minimum order amount for this coupon is {coupon.min_order_amount}."

    # A flat coupon can't make the order free (payments need an amount above 0)
    if coupon.discount_percentage == 0 and coupon.discount_amount >= amount:
        return f"Cart total must be more than the coupon value of {coupon.discount_amount}."

    return None


def calculate_totals(order_items, coupon=None, user=None):
    """
    Price breakdown shared by the cart and checkout.
    The coupon only applies if it's currently usable on this amount.
    """
    subtotal = sum((item.unit_price * item.quantity for item in order_items), Decimal("0.00"))
    discount = sum((item.discount for item in order_items), Decimal("0.00"))

    # Amount after product discounts; coupons and their minimum apply to this
    payable = subtotal - discount

    coupon_discount = Decimal("0.00")
    if coupon and get_coupon_error(coupon, payable, user) is None:
        coupon_discount = coupon.discount_for(payable)

    return {
        "subtotal": subtotal,
        "discount": discount,
        "coupon_discount": coupon_discount,
        "shipping_fee": SHIPPING_FEE,
        "tax": TAX,
        "platform_fee": PLATFORM_FEE,
        "total_amount": payable - coupon_discount + SHIPPING_FEE + TAX + PLATFORM_FEE,
    }


@transaction.atomic
def checkout(user, address, customer_note=None):
    """
    Turn the user's cart into a pending online-payment order.

    Everything runs in one transaction: if the Razorpay call fails,
    the order, its items and the payment row are all rolled back.
    Stock is only checked here; it is reduced once payment succeeds.
    """
    # 1. Validate cart
    cart, cart_items, products = validate_cart(user)

    order = Order(
        user=user,
        payment_method=Order.PaymentMethod.ONLINE,
        shipping_name=address.name,
        shipping_phone_number=address.phone,
        shipping_address=address.address,
        shipping_city=address.city,
        shipping_state=address.state,
        shipping_postal_code=address.postal_code,
        shipping_country=address.country,
        customer_note=customer_note,
    )

    order_items = [
        OrderItem.from_product(order, products[item.product_id], item.quantity)
        for item in cart_items
    ]

    # 2. Calculate total (including the cart's coupon, if still valid)
    coupon = cart.coupon

    if coupon:
        payable = sum((item.total_price for item in order_items), Decimal("0.00"))
        error = get_coupon_error(coupon, payable, user)

        if error:
            raise MessageError(
                f"Coupon {coupon.code} can't be used: {error} Remove it to continue.",
                coupon_code=coupon.code
            )

        order.coupon_code = coupon.code

    for field, value in calculate_totals(order_items, coupon, user).items():
        setattr(order, field, value)

    if order.total_amount <= 0:
        raise MessageError("Order total must be greater than zero.")

    # 3. Create Order
    order.save()

    # 4. Create OrderItems
    for item in order_items:
        item.order = order
    OrderItem.objects.bulk_create(order_items)

    # 5. Create Razorpay Order
    razorpay_order = create_razorpay_order(order)

    # 6. Create Payment
    payment = Payment.objects.create(
        order=order,
        razorpay_order_id=razorpay_order["id"],
        amount=order.total_amount,
        currency=CURRENCY,
    )

    return order, payment, razorpay_order


def get_user_payment(user, razorpay_order_id):
    """Lock and return the user's payment for a Razorpay order, or raise 404."""
    payment = Payment.objects.select_for_update().select_related("order").filter(
        razorpay_order_id=razorpay_order_id,
        order__user=user
    ).first()

    if not payment:
        raise MessageError("Payment not found.", status.HTTP_404_NOT_FOUND)

    return payment


def get_user_order(user, order_id, lock=False):
    orders = Order.objects.select_for_update() if lock else Order.objects
    order = orders.filter(id=order_id, user=user).first()

    if not order:
        raise MessageError("Order not found.", status.HTTP_404_NOT_FOUND)

    return order


def get_payable_order(user, order_id):
    """Return (order, payment) for an order that is still waiting for payment."""
    order = get_user_order(user, order_id)

    if order.status != Order.Status.PENDING or order.payment_status == Order.PaymentStatus.PAID:
        raise MessageError("This order can no longer be paid.")

    payment = Payment.objects.filter(order=order).first()

    if not payment:
        raise MessageError("Payment not found.", status.HTTP_404_NOT_FOUND)

    return order, payment


@transaction.atomic
def confirm_payment(user, razorpay_order_id, razorpay_payment_id, razorpay_signature):
    """
    Called after Razorpay Checkout reports success.

    Verifies the signature, then marks the payment successful and the order
    paid + confirmed, reduces stock and removes the ordered items from the cart.

    Returns (order, problem). problem is None on success; otherwise the payment
    went through but the order can't be fulfilled (it was cancelled, or items
    sold out while the user was paying), so it is cancelled and needs a refund.
    """
    payment = get_user_payment(user, razorpay_order_id)
    order = payment.order

    # Already confirmed (e.g. the frontend retried the request)
    if payment.status == Payment.Status.SUCCESS:
        return order, None

    if not is_valid_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        raise MessageError("Payment verification failed.")

    # The money is taken at this point, so record the payment first
    payment.status = Payment.Status.SUCCESS
    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.save(update_fields=["status", "razorpay_payment_id", "razorpay_signature", "updated_at"])

    order.payment_status = Order.PaymentStatus.PAID

    if order.status != Order.Status.PENDING:
        logger.warning("Order %s paid after it was %s; needs refund", order.order_number, order.status)
        order.save(update_fields=["payment_status", "updated_at"])
        return order, {
            "message": "This order was already cancelled. Your payment will be refunded."
        }

    items = list(order.items.all())
    products = Product.objects.select_for_update().in_bulk(
        [item.product_id for item in items]
    )

    out_of_stock = [
        {
            "product_id": item.product_id,
            "product_name": item.product_name,
            "requested_quantity": item.quantity,
            "available_stock": products[item.product_id].stock,
        }
        for item in items
        if item.quantity > products[item.product_id].stock
    ]

    if out_of_stock:
        logger.warning("Order %s paid but out of stock; needs refund", order.order_number)
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["payment_status", "status", "updated_at"])
        return order, {
            "message": "Some items sold out while you were paying. The order was cancelled and your payment will be refunded.",
            "out_of_stock": out_of_stock,
        }

    for item in items:
        product = products[item.product_id]
        product.stock -= item.quantity
        product.save(update_fields=["stock", "updated_at"])

    order.status = Order.Status.CONFIRMED
    order.save(update_fields=["payment_status", "status", "updated_at"])

    # Remove the ordered products from the cart; keep anything added since checkout
    cart = Cart.objects.filter(user=user).first()
    if cart:
        CartItem.objects.filter(
            cart=cart,
            product_id__in=products.keys()
        ).delete()

        # The coupon was used on this order
        if order.coupon_code and cart.coupon_id:
            cart.coupon = None
            cart.save(update_fields=["coupon", "updated_at"])

        if not cart.items.exists():
            cart.delete()

    return order, None


@transaction.atomic
def record_payment_failure(user, razorpay_order_id, razorpay_payment_id=None, reason=None):
    """
    Called when Razorpay Checkout reports a failed attempt.

    The order stays pending: the user can retry with the same Razorpay order.
    """
    payment = get_user_payment(user, razorpay_order_id)
    order = payment.order

    # A later successful attempt wins over an earlier failure
    if payment.status == Payment.Status.SUCCESS:
        return order

    logger.info("Payment failed for %s: %s", order.order_number, reason)

    payment.status = Payment.Status.FAILED
    if razorpay_payment_id:
        payment.razorpay_payment_id = razorpay_payment_id
    payment.save(update_fields=["status", "razorpay_payment_id", "updated_at"])

    order.payment_status = Order.PaymentStatus.FAILED
    order.save(update_fields=["payment_status", "updated_at"])

    return order


@transaction.atomic
def cancel_order(user, order_id):
    """Cancel an order that hasn't been paid yet."""
    order = get_user_order(user, order_id, lock=True)

    if order.status != Order.Status.PENDING or order.payment_status == Order.PaymentStatus.PAID:
        raise MessageError("Only unpaid pending orders can be cancelled.")

    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])

    return order


# Where the host may move an order from each status
ALLOWED_STATUS_CHANGES = {
    Order.Status.PENDING: [Order.Status.CANCELLED],
    Order.Status.CONFIRMED: [Order.Status.PACKED, Order.Status.CANCELLED],
    Order.Status.PACKED: [Order.Status.IN_TRANSIT, Order.Status.CANCELLED],
    Order.Status.IN_TRANSIT: [Order.Status.DELIVERED],
    Order.Status.DELIVERED: [],
    Order.Status.CANCELLED: [],
}

# Statuses in which the order's stock has already been taken
STOCK_RESERVED_STATUSES = [
    Order.Status.CONFIRMED,
    Order.Status.PACKED,
    Order.Status.IN_TRANSIT,
    Order.Status.DELIVERED,
]


@transaction.atomic
def update_order_status(order_id, new_status):
    """Host: move an order to its next status, restocking a cancelled paid order."""
    order = Order.objects.select_for_update().filter(id=order_id).first()

    if not order:
        raise MessageError("Order not found.", status.HTTP_404_NOT_FOUND)

    allowed = ALLOWED_STATUS_CHANGES[order.status]

    if new_status not in allowed:
        raise MessageError(
            f"Order can't be changed from {order.status} to {new_status}.",
            allowed_statuses=[str(choice) for choice in allowed]
        )

    # Stock was reduced when the payment was confirmed; give it back
    if order.status in STOCK_RESERVED_STATUSES and new_status == Order.Status.CANCELLED:
        items = list(order.items.all())
        products = Product.objects.select_for_update().in_bulk(
            [item.product_id for item in items]
        )

        for item in items:
            product = products[item.product_id]
            product.stock += item.quantity
            product.save(update_fields=["stock", "updated_at"])

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])

    return order

