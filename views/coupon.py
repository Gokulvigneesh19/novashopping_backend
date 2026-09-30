from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from core.permissions import IsHost
from core.responses import message_response
from core.utils import get_object_or_error, validate_or_error
from models import Coupon
from serializers import CouponSerializer


class CouponView(APIView):

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]

        # Creating and editing coupons is for the host (admin login) only
        return [IsAuthenticated(), IsHost()]

    def get_queryset(self):
        # The host sees every coupon; everyone else only live ones
        # (active and between start_date and end_date)
        if self.request.user.is_authenticated and self.request.user.is_host:
            return Coupon.objects.all()

        return Coupon.live()

    # GET COUPONS / GET COUPON
    def get(self, request, coupon_id=None):

        if coupon_id:
            coupon = get_object_or_error(
                self.get_queryset(),
                "Coupon not found.",
                id=coupon_id
            )

            return message_response(
                "Coupon retrieved successfully.",
                coupon=CouponSerializer(coupon).data
            )

        return message_response(
            "Coupons retrieved successfully.",
            coupons=CouponSerializer(self.get_queryset(), many=True).data
        )

    # CREATE COUPON (host only)
    def post(self, request, coupon_id=None):

        serializer = CouponSerializer(data=request.data)
        validate_or_error(serializer, "Failed to create coupon.")
        serializer.save()

        return message_response(
            "Coupon created successfully.",
            status.HTTP_201_CREATED,
            coupon=serializer.data
        )

    # UPDATE COUPON (host only) - send only the fields to change
    def patch(self, request, coupon_id=None):

        if coupon_id is None:
            return message_response(
                "Use coupon ID to update a specific coupon.",
                status.HTTP_400_BAD_REQUEST
            )

        serializer = CouponSerializer(
            get_object_or_error(Coupon, "Coupon not found.", id=coupon_id),
            data=request.data,
            partial=True
        )
        validate_or_error(serializer, "Failed to update coupon.")
        serializer.save()

        return message_response(
            "Coupon updated successfully.",
            coupon=serializer.data
        )

    # DELETE COUPON (host only)
    def delete(self, request, coupon_id=None):

        if coupon_id is None:
            return message_response(
                "Use coupon ID to delete a specific coupon.",
                status.HTTP_400_BAD_REQUEST
            )

        coupon = get_object_or_error(Coupon, "Coupon not found.", id=coupon_id)
        coupon.delete()

        return message_response("Coupon deleted successfully.")
