from rest_framework import serializers

from models import DashboardSnapshot


class DashboardSnapshotSerializer(serializers.ModelSerializer):

    class Meta:
        model = DashboardSnapshot
        fields = [
            "id",
            "date",
            "total_revenue",
            "orders",
            "new_customers",
            "checkouts",
            "conversion_rate",
            "updated_at",
        ]
