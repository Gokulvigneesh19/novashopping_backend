from decimal import Decimal, InvalidOperation

from rest_framework import status
from rest_framework.views import APIView

from core.exceptions import MessageError
from core.permissions import PublicReadHostWriteMixin
from core.responses import message_response
from core.utils import get_object_or_error
from models import Product
from serializers import ProductSerializer


SORT_FILTERS = {
    "best_sellers": {"is_bestseller": True},
    "discounted": {"is_discounted": True},
}

SORT_ORDERING = {
    "price_low_to_high": "price",
    "price_high_to_low": "-price",
}


class ProductView(PublicReadHostWriteMixin, APIView):

    # GET PRODUCTS / GET PRODUCT
    def get(self, request, product_id=None):

        if product_id:
            product = get_object_or_error(
                Product,
                "Product not found.",
                id=product_id,
                is_active=True
            )

            return message_response(
                "Product retrieved successfully.",
                product=self._serialize(product),
                no_of_products=1
            )

        products = self._filter_products(request.query_params)

        return message_response(
            "Products retrieved successfully.",
            products=self._serialize(products, many=True),
            no_of_products=products.count()
        )

    # CREATE PRODUCT
    def post(self, request, product_id=None):

        serializer = ProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Automatically assign logged-in user as host
        product = serializer.save(host=request.user)

        return message_response(
            "Product created successfully.",
            status.HTTP_201_CREATED,
            product=self._serialize(product)
        )

    # UPDATE PRODUCT
    def put(self, request, product_id=None):

        product = self._get_own_product(request, product_id, "update")

        serializer = ProductSerializer(
            product,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return message_response(
            "Product updated successfully.",
            product=serializer.data
        )

    # DELETE PRODUCT
    def delete(self, request, product_id=None):

        self._get_own_product(request, product_id, "delete").delete()

        return message_response("Product deleted successfully.")

    def _serialize(self, instance, many=False):
        return ProductSerializer(
            instance,
            many=many,
            context={"request": self.request}
        ).data

    def _filter_products(self, params):
        products = Product.objects.filter(is_active=True)

        search = params.get("search")
        if search:
            products = products.filter(name__icontains=search)

        try:
            if params.get("min_price"):
                products = products.filter(price__gte=Decimal(params["min_price"]))
            if params.get("max_price"):
                products = products.filter(price__lte=Decimal(params["max_price"]))
        except InvalidOperation:
            raise MessageError("min_price and max_price must be valid numbers.")

        sort = params.get("sort")
        if sort in SORT_FILTERS:
            products = products.filter(**SORT_FILTERS[sort])
        elif sort in SORT_ORDERING:
            products = products.order_by(SORT_ORDERING[sort])

        limit = params.get("limit")
        if limit:
            products = products[:int(limit)]

        return products

    def _get_own_product(self, request, product_id, action):
        """Fetch a product the logged-in host owns; action is "update" or "delete"."""
        if product_id is None:
            raise MessageError(f"Use product ID to {action} a specific product.")

        product = get_object_or_error(
            Product,
            "Product not found.",
            id=product_id
        )

        # Hosts can only change their own products
        if product.host != request.user:
            raise MessageError(
                f"You can only {action} your own products.",
                status.HTTP_403_FORBIDDEN
            )

        return product
