from rest_framework import serializers

from models import Coupon


class CouponSerializer(serializers.ModelSerializer):

    # Active and inside its start/end dates right now
    is_live = serializers.BooleanField(read_only=True)

    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "description",
            "discount_percentage",
            "discount_amount",
            "min_order_amount",
            "start_date",
            "end_date",
            "only_for_new",
            "active",
            "is_live",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "is_live",
            "created_at",
            "updated_at",
        ]

        # Multipart requests treat a missing boolean as False; keep new coupons active
        extra_kwargs = {
            "active": {"default": True},
            "only_for_new": {"default": False},
        }

    def validate_code(self, value):
        # Codes are stored in upper case so "save10" and "SAVE10" are the same code
        code = value.strip().upper()

        if not code:
            raise serializers.ValidationError("Code can't be blank.")

        duplicates = Coupon.objects.filter(code=code)
        if self.instance:
            duplicates = duplicates.exclude(id=self.instance.id)

        if duplicates.exists():
            raise serializers.ValidationError("A coupon with this code already exists.")

        return code

    def validate(self, attrs):
        # A coupon is EITHER a percentage off OR a flat amount off
        percentage = attrs.get("discount_percentage", getattr(self.instance, "discount_percentage", 0)) or 0
        amount = attrs.get("discount_amount", getattr(self.instance, "discount_amount", 0)) or 0

        if percentage > 0 and amount > 0:
            raise serializers.ValidationError(
                {"discount_amount": "Set either discount_percentage or discount_amount, not both."}
            )

        if percentage == 0 and amount == 0:
            raise serializers.ValidationError(
                {"discount_percentage": "Set a discount_percentage or a discount_amount."}
            )

        # On PATCH, compare against the saved value for whichever date isn't being changed
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))

        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError(
                {"end_date": "End date must be after the start date."}
            )

        return attrs

