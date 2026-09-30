from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.exceptions import MessageError
from core.permissions import IsHost
from core.responses import message_response, status_response
from core.utils import get_error_message, get_object_or_error
from models import Order
from serializers import (
    AdminOrderSerializer,
    DashboardSnapshotSerializer,
    LoginSerializer,
    OrderStatusSerializer,
)
from services.dashboard import (
    MAX_SNAPSHOT_DAYS,
    get_dashboard,
    get_snapshots,
    summarize_snapshots,
)
from services.order import update_order_status


class AdminLoginView(APIView):

    # Same as user login, but only the host (is_host=True) gets tokens
    def post(self, request):

        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return status_response(
                False,
                get_error_message(serializer.errors),
                status.HTTP_401_UNAUTHORIZED
            )

        if not serializer.validated_data["user"]["is_host"]:
            return status_response(
                False,
                "You are not authorized to access the admin panel.",
                status.HTTP_403_FORBIDDEN
            )

        return status_response(
            True,
            "Admin login successful.",
            **serializer.validated_data
        )


class AdminAPIView(APIView):

    permission_classes = [IsAuthenticated, IsHost]


class AdminOrderView(AdminAPIView):

    # GET ALL ORDERS / GET ORDER (every customer's orders)
    def get(self, request, order_id=None):

        orders = Order.objects.select_related("user", "payment").prefetch_related("items")

        if order_id:
            order = get_object_or_error(orders, "Order not found.", id=order_id)

            return message_response(
                "Order retrieved successfully.",
                order=AdminOrderSerializer(order, context={"request": request}).data
            )

        params = request.query_params

        if params.get("status"):
            orders = orders.filter(status=params["status"])

        if params.get("payment_status"):
            orders = orders.filter(payment_status=params["payment_status"])

        if params.get("search"):
            orders = orders.filter(
                Q(order_number__icontains=params["search"])
                | Q(user__email__icontains=params["search"])
            )

        return message_response(
            "Orders retrieved successfully.",
            orders=AdminOrderSerializer(orders, many=True, context={"request": request}).data,
            no_of_orders=orders.count()
        )

    # UPDATE ORDER STATUS - PUT /orders/<id>/ {status} or PUT /orders/ {order_id, status}
    def put(self, request, order_id=None):
        return self._update_status(request, order_id)

    # UPDATE ORDER STATUS - PATCH /orders/<id>/ {status}
    def patch(self, request, order_id=None):
        return self._update_status(request, order_id)

    def _update_status(self, request, order_id):

        serializer = OrderStatusSerializer(data=request.data)

        if not serializer.is_valid():
            raise MessageError(
                get_error_message(serializer.errors),
                errors=serializer.errors
            )

        order_id = order_id or serializer.validated_data.get("order_id")

        if not order_id:
            raise MessageError(
                "order_id is required.",
                errors={"order_id": ["This field is required."]}
            )

        order = update_order_status(order_id, serializer.validated_data["status"])

        return message_response(
            "Order status updated successfully.",
            order=AdminOrderSerializer(order, context={"request": request}).data
        )


def get_date_range(request):
    """start_date / end_date query params (YYYY-MM-DD), defaulting to month to date."""
    today = timezone.localdate()
    params = request.query_params

    try:
        start = parse_date(params["start_date"]) if params.get("start_date") else today.replace(day=1)
        end = parse_date(params["end_date"]) if params.get("end_date") else today
    except ValueError:
        start = end = None

    if not start or not end:
        raise MessageError(
            "Dates must be in YYYY-MM-DD format.",
            errors={"date": ["Use YYYY-MM-DD."]}
        )

    if start > end:
        raise MessageError(
            "start_date can't be after end_date.",
            errors={"start_date": ["Must be on or before end_date."]}
        )

    return start, end


class AdminDashboardView(AdminAPIView):

    # GET DASHBOARD - ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD (defaults to month to date)
    def get(self, request):

        start, end = get_date_range(request)

        return message_response(
            "Dashboard retrieved successfully.",
            **get_dashboard(start, end, request)
        )


class AdminDashboardSnapshotView(AdminAPIView):

    # GET DAILY SNAPSHOTS - ?start_date=&end_date=&refresh=true (defaults to month to date)
    def get(self, request):

        start, end = get_date_range(request)

        if (end - start).days >= MAX_SNAPSHOT_DAYS:
            raise MessageError(
                f"Date range can't be longer than {MAX_SNAPSHOT_DAYS} days.",
                errors={"date": [f"At most {MAX_SNAPSHOT_DAYS} days."]}
            )

        refresh = request.query_params.get("refresh", "").lower() in ("1", "true")
        snapshots = get_snapshots(start, end, refresh=refresh)

        return message_response(
            "Dashboard snapshots retrieved successfully.",
            period={"start_date": start, "end_date": end},
            summary=summarize_snapshots(snapshots),
            snapshots=DashboardSnapshotSerializer(snapshots, many=True).data,
            no_of_snapshots=len(snapshots)
        )
