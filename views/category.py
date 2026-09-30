from rest_framework import status
from rest_framework.views import APIView

from core.permissions import PublicReadHostWriteMixin
from core.responses import message_response
from core.utils import get_object_or_error, validate_or_error
from models import Category, Product
from serializers import CategorySerializer, ProductSerializer


def get_active_category(category_id):
    return get_object_or_error(
        Category,
        "Category not found.",
        id=category_id,
        is_active=True
    )


class CategoryView(PublicReadHostWriteMixin, APIView):

    # GET CATEGORIES / GET CATEGORY
    def get(self, request, category_id=None):

        if category_id:
            category = get_active_category(category_id)

            return message_response(
                "Category retrieved successfully.",
                category=CategorySerializer(category).data
            )

        categories = Category.objects.filter(is_active=True)

        return message_response(
            "Categories retrieved successfully.",
            categories=CategorySerializer(categories, many=True).data
        )

    # POST CATEGORY
    def post(self, request):

        serializer = CategorySerializer(data=request.data)
        validate_or_error(serializer, "Failed to create category.")
        serializer.save()

        return message_response(
            "Category created successfully.",
            status.HTTP_201_CREATED,
            category=serializer.data
        )

    # UPDATE CATEGORY
    def put(self, request, category_id):

        serializer = CategorySerializer(
            get_active_category(category_id),
            data=request.data,
            partial=True
        )
        validate_or_error(serializer, "Failed to update category.")
        serializer.save()

        return message_response(
            "Category updated successfully.",
            category=serializer.data
        )

    # DELETE CATEGORY (soft delete)
    def delete(self, request, category_id):

        category = get_active_category(category_id)
        category.is_active = False
        category.save()

        return message_response("Category deleted successfully.")


class CategoryProductsView(APIView):

    def get(self, request, category_id):

        category = get_active_category(category_id)

        products = Product.objects.filter(
            category=category,
            is_active=True
        ).order_by("-created_at")

        serializer = ProductSerializer(
            products,
            many=True,
            context={"request": request}
        )

        return message_response(
            "Category products retrieved successfully.",
            category={
                "id": category.id,
                "name": category.name
            },
            products=serializer.data
        )
