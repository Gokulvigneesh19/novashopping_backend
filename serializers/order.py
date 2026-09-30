from rest_framework import serializers

from models import Order, OrderItem, Payment


class CheckoutSerializer(serializers.Serializer):

    # Defaults to the user's default address when omitted
    address_id = serializers.UUIDField(required=False)

    customer_note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )

    def validate(self, attrs):
        user = self.context["request"].user
        address_id = attrs.get("address_id")

        if address_id:
            address = user.addresses.filter(id=address_id).first()

            if not address:
                raise serializers.ValidationError(
                    {"address_id": "Address not found."}
                )
        else:
            address = user.addresses.filter(is_default=True).first()

            if not address:
                raise serializers.ValidationError(
                    {"address_id": "Please add a delivery address."}
                )

        attrs["address"] = address
        return attrs


class VerifyPaymentSerializer(serializers.Serializer):
    """The three values Razorpay Checkout passes to its success handler."""

    razorpay_order_id = serializers.CharField(max_length=255)
    razorpay_payment_id = serializers.CharField(max_length=255)
    razorpay_signature = serializers.CharField(max_length=500)


class PaymentFailedSerializer(serializers.Serializer):
    """Values from Razorpay Checkout's "payment.failed" event."""

    razorpay_order_id = serializers.CharField(max_length=255)
    razorpay_payment_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment
        fields = [
            "id",
            "provider",
            "razorpay_order_id",
            "razorpay_payment_id",
            "amount",
            "currency",
            "status",
            "created_at",
            "updated_at",
        ]


class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_image",
            "unit_price",
            "discount_percentage",
            "quantity",
            "discount",
            "tax",
            "total_price",
        ]


class OrderSerializer(serializers.ModelSerializer):

    items = OrderItemSerializer(many=True, read_only=True)

    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "payment_status",
            "payment_method",
            "shipping_name",
            "shipping_phone_number",
            "shipping_address",
            "shipping_city",
            "shipping_state",
            "shipping_postal_code",
            "shipping_country",
            "subtotal",
            "discount",
            "coupon_code",
            "coupon_discount",
            "shipping_fee",
            "tax",
            "platform_fee",
            "total_amount",
            "customer_note",
            "items",
            "payment",
            "created_at",
            "updated_at",
        ]


class AdminOrderSerializer(OrderSerializer):

    user_id = serializers.UUIDField(source="user.id", read_only=True)

    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = ["user_id", "user_email"] + OrderSerializer.Meta.fields


class OrderStatusSerializer(serializers.Serializer):

    # Only needed when the order ID isn't in the URL
    order_id = serializers.UUIDField(required=False)

    status = serializers.ChoiceField(choices=Order.Status.choices)

