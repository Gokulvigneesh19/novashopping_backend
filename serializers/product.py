from django.db.models import Avg, Count

from rest_framework import serializers

from models import CartItem, Category, Product, ProductImage, ReviewAndRating, WishlistItem

from .review import ReviewAndRatingSerializer


class ProductImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductImage
        fields = ["id", "image"]


class ProductSerializer(serializers.ModelSerializer):

    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.filter(is_active=True)
    )

    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    host_email = serializers.EmailField(
        source="host.email",
        read_only=True
    )

    price_after_discount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    # Upload multiple files under the same "sub_images" key;
    # responses list the saved images (see to_representation)
    sub_images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )

    # IDs of existing sub-images to delete on update
    remove_sub_image_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    is_wishlisted = serializers.SerializerMethodField()

    reviews = serializers.SerializerMethodField()

    average_rating = serializers.SerializerMethodField()

    total_ratings = serializers.SerializerMethodField()

    is_cart_added = serializers.SerializerMethodField()

    def create(self, validated_data):
        uploaded_sub_images = validated_data.pop("sub_images", [])
        validated_data.pop("remove_sub_image_ids", None)

        product = super().create(validated_data)

        for image in uploaded_sub_images:
            ProductImage.objects.create(product=product, image=image)

        return product

    def update(self, instance, validated_data):
        uploaded_sub_images = validated_data.pop("sub_images", [])
        remove_sub_image_ids = validated_data.pop("remove_sub_image_ids", [])

        product = super().update(instance, validated_data)

        if remove_sub_image_ids:
            for sub_image in product.sub_images.filter(id__in=remove_sub_image_ids):
                sub_image.image.delete(save=False)
                sub_image.delete()

        for image in uploaded_sub_images:
            ProductImage.objects.create(product=product, image=image)

        return product

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["sub_images"] = ProductImageSerializer(
            instance.sub_images.all(),
            many=True,
            context=self.context
        ).data
        return data

    def get_is_wishlisted(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return False

        return WishlistItem.objects.filter(
            wishlist__user=request.user,
            product=obj
        ).exists()

    def get_is_cart_added(self, obj):
        request = self.context.get("request")

        if not request:
            return False

        if not request.user.is_authenticated:
            return CartItem.objects.filter(
                cart__session_key=request.session.session_key,
                cart__user__isnull=True,
                product_id=obj.id
            ).exists()

        return CartItem.objects.filter(
            cart__user=request.user,
            product_id=obj.id
        ).exists()

    def get_reviews(self, obj):
        reviews = ReviewAndRating.objects.filter(product=obj)
        return ReviewAndRatingSerializer(reviews, many=True).data

    def _get_rating_stats(self, obj):
        if not hasattr(obj, "_rating_stats"):
            obj._rating_stats = ReviewAndRating.objects.filter(
                product=obj
            ).aggregate(
                average_rating=Avg("rating"),
                total_ratings=Count("id")
            )

        return obj._rating_stats

    def get_average_rating(self, obj):
        average_rating = self._get_rating_stats(obj)["average_rating"]
        return round(average_rating, 2) if average_rating is not None else 0

    def get_total_ratings(self, obj):
        return self._get_rating_stats(obj)["total_ratings"]


    class Meta:
        model = Product

        fields = [
            "id",
            "category_id",
            "category_name",
            "host",
            "host_email",
            "name",
            "description",
            "price",
            "discount_percentage",
            "price_after_discount",
            "stock",
            "cover_image",
            "sub_images",
            "remove_sub_image_ids",
            "reviews",
            "average_rating",
            "total_ratings",
            "is_wishlisted",
            "is_cart_added",
            "is_bestseller",
            "is_discounted",
            "is_active",
            "created_at",
            "updated_at",
        ]

        # Multipart requests treat a missing boolean as False; keep new products active
        extra_kwargs = {
            "is_active": {"default": True},
        }

        read_only_fields = [
            "id",
            "category_name",
            "host",
            "host_email",
            "reviews",
            "average_rating",
            "total_ratings",
            "price_after_discount",
            "created_at",
            "updated_at",
        ]
