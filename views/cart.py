from rest_framework import status
from rest_framework.views import APIView

from core.exceptions import MessageError
from core.responses import message_response
from core.utils import get_object_or_error
from models import CartItem
from serializers import CartItemSerializer
from services import (
    apply_coupon,
    get_cart_totals,
    get_or_create_request_cart,
    get_request_cart,
    remove_coupon,
)


def check_stock(product, quantity, **extra):
    if quantity > product.stock:
        raise MessageError(
            "Requested quantity is greater than available stock.",
            available_stock=product.stock,
            **extra
        )


def get_cart_or_error(request):
    cart = get_request_cart(request)

    if not cart:
        raise MessageError("Cart not found.", status.HTTP_404_NOT_FOUND)

    return cart


def cart_data(cart):
    """The full cart: items plus totals (subtotal, discount, coupon, cart_amount)."""
    if not cart:
        return {
            "id": None,
            "items": [],
            **get_cart_totals([])
        }

    items = list(cart.items.select_related("product"))

    return {
        "id": str(cart.id),
        "items": CartItemSerializer(items, many=True).data,
        **get_cart_totals(items, cart.coupon, cart.user)
    }


class CartView(APIView):

    # GET CART
    def get(self, request):

        return message_response(
            "Cart retrieved successfully.",
            cart=cart_data(get_request_cart(request))
        )

    # ADD PRODUCT TO CART
    def post(self, request):

        cart = get_or_create_request_cart(request)

        serializer = CartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        check_stock(product, quantity)

        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                "quantity": quantity
            }
        )

        # If already in the cart, increase quantity
        if not item_created:
            new_quantity = cart_item.quantity + quantity

            check_stock(product, new_quantity, current_quantity=cart_item.quantity)

            cart_item.quantity = new_quantity
            cart_item.save()

        return message_response(
            "Product added to cart successfully.",
            status.HTTP_201_CREATED,
            item=CartItemSerializer(cart_item).data
        )

    # UPDATE CART ITEM QUANTITY
    def put(self, request, item_id):

        cart_item = get_object_or_error(
            CartItem.objects.select_related("product"),
            "Cart item not found.",
            id=item_id,
            cart=get_cart_or_error(request)
        )

        try:
            quantity = int(request.data.get("quantity"))
        except (TypeError, ValueError):
            raise MessageError("Quantity must be a valid integer.")

        if quantity <= 0:
            raise MessageError("Quantity must be greater than zero.")

        check_stock(cart_item.product, quantity)

        cart_item.quantity = quantity
        cart_item.save()

        return message_response(
            "Cart item quantity updated successfully.",
            item=CartItemSerializer(cart_item).data
        )

    # REMOVE ITEM FROM CART
    def delete(self, request, item_id):

        cart = get_cart_or_error(request)

        cart_item = get_object_or_error(
            CartItem,
            "Cart item not found.",
            id=item_id,
            cart=cart
        )

        deleted_product_id = cart_item.product_id

        cart_item.delete()

        # Delete cart if no items remain
        if not cart.items.exists():
            cart.delete()

        return message_response(
            "Product removed from cart successfully.",
            product_id=deleted_product_id
        )


class CartCountView(APIView):

    # GET CART ITEM COUNT
    def get(self, request):

        cart = get_request_cart(request)

        return message_response(
            "Cart count retrieved successfully.",
            count=cart.items.count() if cart else 0
        )


class CartCouponView(APIView):

    # APPLY COUPON - {"code": "SAVE10"}
    def post(self, request):

        cart, _ = apply_coupon(get_request_cart(request), request.data.get("code"))

        return message_response(
            f"Coupon {cart.coupon.code} applied successfully.",
            cart=cart_data(cart)
        )

    # REMOVE COUPON
    def delete(self, request):

        cart = get_request_cart(request)
        remove_coupon(cart)

        return message_response(
            "Coupon removed successfully.",
            cart=cart_data(cart)
        )

