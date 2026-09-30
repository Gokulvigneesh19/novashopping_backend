from decimal import Decimal

from rest_framework import serializers

from models import CartItem


class CartItemSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="product.name",
        read_only=True
    )

    product_price = serializers.DecimalField(
        source="product.price",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    discount_percentage = serializers.DecimalField(
        source="product.discount_percentage",
        max_digits=5,
        decimal_places=2,
        read_only=True
    )

    price_after_discount = serializers.DecimalField(
        source="product.price_after_discount",
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    # price_after_discount x quantity for this line
    total_price = serializers.SerializerMethodField()

    image = serializers.ImageField(
        source="product.cover_image",
        read_only=True
    )

    class Meta:
        model = CartItem

        fields = [
            "id",
            "product",
            "product_name",
            "product_price",
            "discount_percentage",
            "price_after_discount",
            "image",
            "quantity",
            "total_price",
        ]

        read_only_fields = [
            "id",
            "product_name",
            "product_price",
            "discount_percentage",
            "price_after_discount",
            "image",
        ]

    def get_total_price(self, obj):
        unit_price = obj.product.price_after_discount.quantize(Decimal("0.01"))
        return str(unit_price * obj.quantity)

    def validate_product(self, product):

        if not product.is_active:
            raise serializers.ValidationError(
                "This product is not available."
            )

        if product.stock <= 0:
            raise serializers.ValidationError(
                "This product is out of stock."
            )

        return product

    def validate_quantity(self, quantity):

        if quantity < 1:
            raise serializers.ValidationError(
                "Quantity must be at least 1."
            )

        return quantity
