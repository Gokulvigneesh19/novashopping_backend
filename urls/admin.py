from django.urls import path

from views import AdminDashboardSnapshotView, AdminDashboardView, AdminLoginView, AdminOrderView


# Mounted at /api/admin/ (Django's own admin site stays at /admin/)
urlpatterns = [
    path("login/", AdminLoginView.as_view(), name="admin-login"),
    path("dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("dashboard/snapshots/", AdminDashboardSnapshotView.as_view(), name="admin-dashboard-snapshots"),
    path("orders/", AdminOrderView.as_view(), name="admin-orders"),
    path("orders/<uuid:order_id>/", AdminOrderView.as_view(), name="admin-order-detail"),
]
