from rest_framework import serializers

from models import Product, ReviewAndRating


class ReviewAndRatingSerializer(serializers.ModelSerializer):

    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
        write_only=True
    )

    user_email = serializers.EmailField(
        source="user.email",
        read_only=True
    )

    product_name = serializers.CharField(
        source="product.name",
        read_only=True
    )

    class Meta:
        model = ReviewAndRating

        fields = [
            "id",
            "user",
            "user_email",
            "product",
            "product_id",
            "product_name",
            "rating",
            "review",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "user",
            "user_email",
            "product",
            "product_name",
            "created_at",
            "updated_at",
        ]
