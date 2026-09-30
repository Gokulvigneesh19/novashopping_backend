from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from core.permissions import IsHost
from core.responses import message_response
from core.utils import get_object_or_error
from models import Product, ReviewAndRating
from serializers import ReviewAndRatingSerializer


class ReviewAndRatingView(APIView):

    def get_permissions(self):
        # Listing every review is for the host (admin login) only
        if self.request.method == "GET":
            return [IsAuthenticated(), IsHost()]

        # Any logged-in customer can post a review
        return [IsAuthenticated()]

    # All reviews and ratings from all users (host only)
    def get(self, request):
        reviews = ReviewAndRating.objects.select_related(
            "user",
            "product"
        ).order_by("-created_at")

        return message_response(
            "Reviews and ratings retrieved successfully.",
            reviews=ReviewAndRatingSerializer(reviews, many=True).data,
            no_of_reviews=reviews.count()
        )

    def post(self, request):
        serializer = ReviewAndRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review = serializer.save(user=request.user)

        return message_response(
            "Review and rating submitted successfully.",
            status.HTTP_201_CREATED,
            review=ReviewAndRatingSerializer(review).data
        )


class ProductReviewsView(APIView):

    permission_classes = [AllowAny]

    # Reviews and ratings given by all users for a specific product
    def get(self, request, product_id):

        product = get_object_or_error(
            Product,
            "Product not found.",
            id=product_id
        )

        reviews = ReviewAndRating.objects.filter(
            product=product
        ).select_related("user")

        return message_response(
            "Product reviews and ratings retrieved successfully.",
            reviews=ReviewAndRatingSerializer(reviews, many=True).data
        )
