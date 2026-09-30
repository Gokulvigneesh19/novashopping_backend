from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.responses import message_response
from core.utils import get_object_or_error
from serializers import AddressSerializer
from services.address import delete_address


class AddressView(APIView):

    permission_classes = [IsAuthenticated]

    # GET ADDRESSES / GET ADDRESS
    def get(self, request, address_id=None):

        if address_id:
            return message_response(
                "Address retrieved successfully.",
                address=AddressSerializer(self._get_address(address_id)).data
            )

        return message_response(
            "Addresses retrieved successfully.",
            addresses=AddressSerializer(request.user.addresses.all(), many=True).data
        )

    # ADD ADDRESS
    def post(self, request):

        serializer = AddressSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        address = serializer.save()

        return message_response(
            "Address added successfully.",
            status.HTTP_201_CREATED,
            address=AddressSerializer(address).data
        )

    # UPDATE ADDRESS - PUT
    def put(self, request, address_id):
        return self._update(request, address_id, partial=False)

    # UPDATE ADDRESS - PATCH
    def patch(self, request, address_id):
        return self._update(request, address_id, partial=True)

    # DELETE ADDRESS
    def delete(self, request, address_id):

        delete_address(self._get_address(address_id))

        return message_response("Address deleted successfully.")

    def _get_address(self, address_id):
        # Users can only see and change their own addresses
        return get_object_or_error(
            self.request.user.addresses,
            "Address not found.",
            id=address_id
        )

    def _update(self, request, address_id, partial):

        serializer = AddressSerializer(
            self._get_address(address_id),
            data=request.data,
            partial=partial,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        address = serializer.save()

        return message_response(
            "Address updated successfully.",
            address=AddressSerializer(address).data
        )
