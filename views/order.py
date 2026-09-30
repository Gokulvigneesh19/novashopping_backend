from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.exceptions import MessageError
from core.responses import message_response
from core.utils import get_error_message
from serializers import (
    CheckoutSerializer,
    OrderSerializer,
    PaymentFailedSerializer,
    VerifyPaymentSerializer,
)
from services.order import (
    cancel_order,
    checkout,
    confirm_payment,
    get_payable_order,
    get_user_order,
    record_payment_failure,
)
from services.payment import razorpay_checkout_options


def validated_data(serializer_class, request):
    serializer = serializer_class(
        data=request.data,
        context={"request": request}
    )

    if not serializer.is_valid():
        raise MessageError(
            get_error_message(serializer.errors),
            errors=serializer.errors
        )

    return serializer.validated_data


class OrderAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def serialize(self, order):
        return OrderSerializer(order, context={"request": self.request}).data


class CheckoutView(OrderAPIView):

    # Cart -> pending order -> Razorpay order
    def post(self, request):

        data = validated_data(CheckoutSerializer, request)

        order, payment, _ = checkout(
            request.user,
            data["address"],
            data.get("customer_note"),
        )

        return message_response(
            "Order created successfully.",
            status.HTTP_201_CREATED,
            order=self.serialize(order),
            razorpay=razorpay_checkout_options(order, payment)
        )


class VerifyPaymentView(OrderAPIView):

    # Razorpay success handler -> verify signature -> confirm order
    def post(self, request):

        data = validated_data(VerifyPaymentSerializer, request)

        order, problem = confirm_payment(
            request.user,
            data["razorpay_order_id"],
            data["razorpay_payment_id"],
            data["razorpay_signature"],
        )

        if problem:
            return message_response(
                problem["message"],
                status.HTTP_409_CONFLICT,
                order=self.serialize(order),
                **({"out_of_stock": problem["out_of_stock"]} if "out_of_stock" in problem else {})
            )

        return message_response(
            "Payment successful. Your order is confirmed.",
            order=self.serialize(order)
        )


class PaymentFailedView(OrderAPIView):

    # Razorpay "payment.failed" handler -> record the failed attempt
    def post(self, request):

        data = validated_data(PaymentFailedSerializer, request)

        order = record_payment_failure(
            request.user,
            data["razorpay_order_id"],
            data.get("razorpay_payment_id"),
            data.get("reason"),
        )

        return message_response(
            "Payment failed. You can retry the payment for this order.",
            order=self.serialize(order)
        )


class OrderView(OrderAPIView):

    # GET ORDERS / GET ORDER
    def get(self, request, order_id=None):

        if order_id:
            return message_response(
                "Order retrieved successfully.",
                order=self.serialize(get_user_order(request.user, order_id))
            )

        orders = request.user.orders.prefetch_related("items").select_related("payment")

        return message_response(
            "Orders retrieved successfully.",
            orders=OrderSerializer(orders, many=True, context={"request": request}).data
        )


class OrderPayView(OrderAPIView):

    # Reopen Razorpay Checkout for an unpaid pending order
    def post(self, request, order_id):

        order, payment = get_payable_order(request.user, order_id)

        return message_response(
            "Payment details retrieved successfully.",
            order=self.serialize(order),
            razorpay=razorpay_checkout_options(order, payment)
        )


class OrderCancelView(OrderAPIView):

    # Cancel an unpaid pending order
    def post(self, request, order_id):

        return message_response(
            "Order cancelled successfully.",
            order=self.serialize(cancel_order(request.user, order_id))
        )
