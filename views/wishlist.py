from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.responses import message_response
from models import Product, Wishlist, WishlistItem
from serializers import WishlistSerializer


class WishlistView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        wishlist, _ = Wishlist.objects.get_or_create(
            user=request.user
        )

        return Response(WishlistSerializer(wishlist).data)

    def post(self, request):

        product = get_object_or_404(
            Product,
            id=request.data.get("product_id")
        )

        wishlist, _ = Wishlist.objects.get_or_create(
            user=request.user
        )

        _, item_created = WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            product=product
        )

        return message_response(
            "Product added to wishlist"
            if item_created
            else "Product already in wishlist"
        )

    def delete(self, request, product_id):

        item = get_object_or_404(
            WishlistItem,
            wishlist=get_object_or_404(Wishlist, user=request.user),
            product_id=product_id
        )

        item.delete()

        return message_response("Product removed from wishlist")
