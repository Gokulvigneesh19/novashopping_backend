from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, F, Min, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from models import DashboardSnapshot, Order, OrderItem, Product


LOW_STOCK_THRESHOLD = 5

# Longest range the snapshot API will build in one request
MAX_SNAPSHOT_DAYS = 366

# Orders whose payment went through (refunded ones still count as placed orders)
PLACED_PAYMENT_STATUSES = [Order.PaymentStatus.PAID, Order.PaymentStatus.REFUNDED]


def shift_months(day, months):
    """`day` moved by `months`, clamped to the last day of the target month."""
    month_index = day.year * 12 + day.month - 1 + months
    year, month = divmod(month_index, 12)
    month += 1

    return date(year, month, min(day.day, monthrange(year, month)[1]))


def day_range(start, end):
    """Aware datetimes covering `start` 00:00 up to (not including) the day after `end`."""
    tz = timezone.get_current_timezone()

    return (
        timezone.make_aware(datetime.combine(start, time.min), tz),
        timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min), tz),
    )


def placed_orders():
    return Order.objects.filter(payment_status__in=PLACED_PAYMENT_STATUSES)


def revenue_orders():
    """Orders that earned money: paid and not cancelled."""
    return Order.objects.filter(payment_status=Order.PaymentStatus.PAID).exclude(
        status=Order.Status.CANCELLED
    )


def percent_change(current, previous):
    if not previous:
        return None if current else 0.0

    return round(float((Decimal(current) - Decimal(previous)) / Decimal(previous) * 100), 1)


def period_stats(start, end):
    start_at, end_at = day_range(start, end)
    in_period = Q(created_at__gte=start_at, created_at__lt=end_at)

    revenue = revenue_orders().filter(in_period).aggregate(
        total=Sum("total_amount")
    )["total"] or Decimal("0")

    orders = placed_orders().filter(in_period).count()

    # A customer is new in the period their first paid order falls in
    new_customers = (
        Order.objects.filter(payment_status=Order.PaymentStatus.PAID)
        .values("user")
        .annotate(first_order_at=Min("created_at"))
        .filter(first_order_at__gte=start_at, first_order_at__lt=end_at)
        .count()
    )

    # Checkout conversion: share of started checkouts that ended up paid
    checkouts = Order.objects.filter(in_period).count()
    conversion_rate = round(orders / checkouts * 100, 1) if checkouts else 0.0

    return {
        "total_revenue": revenue,
        "orders": orders,
        "new_customers": new_customers,
        "conversion_rate": conversion_rate,
    }


def get_stats(start, end):
    current = period_stats(start, end)
    previous = period_stats(shift_months(start, -1), shift_months(end, -1))

    return {
        key: {
            "value": value,
            "previous": previous[key],
            "change_percentage": percent_change(value, previous[key]),
        }
        for key, value in current.items()
    }


def get_revenue_chart(end, months=12):
    """Revenue per month for the `months` months ending with `end`'s month."""
    first_month = shift_months(end.replace(day=1), -(months - 1))
    start_at, end_at = day_range(first_month, end)

    rows = (
        revenue_orders()
        .filter(created_at__gte=start_at, created_at__lt=end_at)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(revenue=Sum("total_amount"), orders=Count("id"))
    )
    by_month = {row["month"].date().replace(day=1): row for row in rows}

    points = []
    for index in range(months):
        month = shift_months(first_month, index)
        row = by_month.get(month, {})

        points.append({
            "month": month.strftime("%Y-%m"),
            "label": month.strftime("%b"),
            "revenue": row.get("revenue") or Decimal("0"),
            "orders": row.get("orders") or 0,
        })

    return {
        "total": sum((point["revenue"] for point in points), Decimal("0")),
        "this_month": points[-1]["revenue"],
        "months": points,
    }


def revenue_items(start, end):
    start_at, end_at = day_range(start, end)

    return OrderItem.objects.filter(
        order__in=revenue_orders(),
        order__created_at__gte=start_at,
        order__created_at__lt=end_at,
    )


def get_sales_by_category(start, end, limit=5):
    rows = list(
        revenue_items(start, end)
        .values(category_id=F("product__category_id"), name=F("product__category__name"))
        .annotate(amount=Sum("total_price"))
        .order_by("-amount")
    )
    total = sum((row["amount"] for row in rows), Decimal("0"))

    return {
        "total": total,
        "categories": [
            {
                **row,
                "percentage": round(float(row["amount"] / total * 100), 1) if total else 0.0,
            }
            for row in rows[:limit]
        ],
    }


def get_top_products(start, end, request, limit=5):
    rows = list(
        revenue_items(start, end)
        .values("product")
        .annotate(units_sold=Sum("quantity"), revenue=Sum("total_price"))
        .order_by("-units_sold", "-revenue")[:limit]
    )
    products = Product.objects.select_related("category").in_bulk([row["product"] for row in rows])

    top_products = []
    for row in rows:
        product = products[row["product"]]

        top_products.append({
            "id": product.id,
            "name": product.name,
            "category": product.category.name,
            "cover_image": request.build_absolute_uri(product.cover_image.url) if product.cover_image else None,
            "price": product.price_after_discount.quantize(Decimal("0.01")),
            "is_bestseller": product.is_bestseller,
            "units_sold": row["units_sold"],
            "revenue": row["revenue"],
        })

    return top_products


def get_recent_orders(limit=6):
    orders = (
        placed_orders()
        .select_related("user")
        .prefetch_related("items")[:limit]
    )

    recent_orders = []
    for order in orders:
        items = list(order.items.all())
        customer_name = order.user.get_full_name() or order.shipping_name

        recent_orders.append({
            "id": order.id,
            "order_number": order.order_number,
            "customer_name": customer_name,
            "customer_email": order.user.email,
            "product_name": items[0].product_name if items else "",
            "other_items_count": max(len(items) - 1, 0),
            "created_at": order.created_at,
            "status": order.status,
            "status_display": order.get_status_display(),
            "payment_status": order.payment_status,
            "total_amount": order.total_amount,
        })

    return recent_orders


def get_low_stock(threshold=LOW_STOCK_THRESHOLD, limit=5):
    products = Product.objects.filter(is_active=True, stock__lte=threshold).order_by("stock", "name")

    return {
        "threshold": threshold,
        "count": products.count(),
        "products": [
            {"id": product.id, "name": product.name, "stock": product.stock}
            for product in products[:limit]
        ],
    }


def get_dashboard(start, end, request):
    return {
        "period": {"start_date": start, "end_date": end},
        "stats": get_stats(start, end),
        "revenue_chart": get_revenue_chart(end),
        "sales_by_category": get_sales_by_category(start, end),
        "recent_orders": get_recent_orders(),
        "top_products": get_top_products(start, end, request),
        "low_stock": get_low_stock(),
    }


def save_snapshot(day):
    """Compute `day`'s stats from orders and store them."""
    start_at, end_at = day_range(day, day)
    checkouts = Order.objects.filter(created_at__gte=start_at, created_at__lt=end_at).count()

    snapshot, _ = DashboardSnapshot.objects.update_or_create(
        date=day,
        defaults={**period_stats(day, day), "checkouts": checkouts}
    )

    return snapshot


def get_snapshots(start, end, refresh=False):
    """
    Daily snapshots from `start` to `end`. Missing days are computed and saved.
    Today (still changing) and, with `refresh`, every day in the range are recomputed.
    """
    today = timezone.localdate()
    end = min(end, today)

    existing = {
        snapshot.date: snapshot
        for snapshot in DashboardSnapshot.objects.filter(date__gte=start, date__lte=end)
    }

    snapshots = []
    day = start
    while day <= end:
        snapshot = existing.get(day)

        if refresh or snapshot is None or day == today:
            snapshot = save_snapshot(day)

        snapshots.append(snapshot)
        day += timedelta(days=1)

    return snapshots


def summarize_snapshots(snapshots):
    """Totals for the range; conversion rate is total paid orders / total checkouts."""
    orders = sum(snapshot.orders for snapshot in snapshots)
    checkouts = sum(snapshot.checkouts for snapshot in snapshots)

    return {
        "total_revenue": sum((snapshot.total_revenue for snapshot in snapshots), Decimal("0")),
        "orders": orders,
        "new_customers": sum(snapshot.new_customers for snapshot in snapshots),
        "checkouts": checkouts,
        "conversion_rate": round(orders / checkouts * 100, 1) if checkouts else 0.0,
    }
