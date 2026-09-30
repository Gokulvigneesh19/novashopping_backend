from rest_framework import serializers

from models import Product, Wishlist, WishlistItem


class WishlistProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = "__all__"


class WishlistItemSerializer(serializers.ModelSerializer):
    product = WishlistProductSerializer(read_only=True)

    class Meta:
        model = WishlistItem
        fields = [
            "id",
            "product",
            "created_at",
        ]


class WishlistSerializer(serializers.ModelSerializer):

    items = WishlistItemSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Wishlist
        fields = [
            "id",
            "items",
            "created_at",
            "updated_at",
        ]
