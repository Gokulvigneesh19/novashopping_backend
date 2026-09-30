from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.responses import status_response
from core.utils import get_error_message
from models import Order, User
from serializers import LoginSerializer, ProfileSerializer, SignupSerializer, UserSerializer
from services import merge_guest_cart


def error_response(serializer, status_code=status.HTTP_400_BAD_REQUEST):
    return status_response(
        False,
        get_error_message(serializer.errors),
        status_code
    )


class SignupView(APIView):

    def post(self, request):

        # Capture guest session BEFORE signup
        guest_session_key = request.session.session_key

        serializer = SignupSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return error_response(serializer)

        result = serializer.save()

        user = result["user"]

        # Merge guest cart into newly created user's cart
        merge_guest_cart(
            guest_session_key,
            user
        )

        return status_response(
            True,
            "User registered successfully.",
            status.HTTP_201_CREATED,
            refresh=result["refresh"],
            access=result["access"],
            user={
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "phone_code": user.phone_code,
                "is_host": user.is_host,
            }
        )


class LoginView(APIView):

    def post(self, request):

        guest_session_key = request.session.session_key

        serializer = LoginSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return error_response(serializer, status.HTTP_401_UNAUTHORIZED)

        user = User.objects.get(
            id=serializer.validated_data["user"]["id"]
        )
        merge_guest_cart(guest_session_key, user)

        return status_response(
            True,
            "Login successful.",
            **serializer.validated_data
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    # GET PROFILE
    def get(self, request):
        serializer = ProfileSerializer(request.user)

        return status_response(
            True,
            "Profile retrieved successfully.",
            user=serializer.data
        )

    # UPDATE PROFILE - PUT
    def put(self, request):
        return self._update(request, partial=False)

    # UPDATE PROFILE - PATCH
    def patch(self, request):
        return self._update(request, partial=True)

    # DELETE ACCOUNT
    def delete(self, request):
        user = request.user

        # Soft delete
        user.is_active = False
        user.save()

        return status_response(
            True,
            "Account deactivated successfully."
        )

    def _update(self, request, partial):
        serializer = ProfileSerializer(
            request.user,
            data=request.data,
            partial=partial
        )

        if not serializer.is_valid():
            return error_response(serializer)

        serializer.save()

        return status_response(
            True,
            "Profile updated successfully.",
            user=serializer.data
        )


class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    # GET all users
    def get(self, request):
        completed = Q(
            orders__status=Order.Status.DELIVERED,
            orders__payment_status=Order.PaymentStatus.PAID
        )

        # Customers only; the host (shop owner) isn't listed
        users = User.objects.filter(is_active=True, is_host=False).annotate(
            completed_orders=Count("orders", filter=completed),
            total_spent=Coalesce(
                Sum("orders__total_amount", filter=completed),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
        )
        serializer = UserSerializer(
            users,
            many=True,
            context={"request": request}
        )

        # Same completed-order rule, across every listed user
        totals = Order.objects.filter(
            user__is_active=True,
            user__is_host=False,
            status=Order.Status.DELIVERED,
            payment_status=Order.PaymentStatus.PAID
        ).aggregate(
            total_spent=Sum("total_amount"),
            paying_customers=Count("user", distinct=True)
        )
        total_spent = totals["total_spent"] or Decimal("0")
        paying_customers = totals["paying_customers"]

        return status_response(
            True,
            "Users retrieved successfully.",
            users=serializer.data,
            total_spent=total_spent,
            # Average per customer with at least one completed order
            average_spent=(
                (total_spent / paying_customers).quantize(Decimal("0.01"))
                if paying_customers else Decimal("0.00")
            ),
            paying_customers=paying_customers,
            users_count=users.count()
        )
