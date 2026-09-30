from django.db import transaction
from rest_framework import serializers

from models import Address
from services.address import clear_default_address


class AddressSerializer(serializers.ModelSerializer):

    class Meta:
        model = Address
        fields = [
            "id",
            "address_type",
            "name",
            "phone",
            "address",
            "city",
            "state",
            "postal_code",
            "country",
            "is_default",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user

        # The first address is always the default
        if not Address.objects.filter(user=user).exists():
            validated_data["is_default"] = True

        # A new default replaces the old one
        if validated_data.get("is_default"):
            clear_default_address(user)

        return Address.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):

        if validated_data.get("is_default"):
            clear_default_address(instance.user, exclude=instance)

        # The default can only move to another address, not be removed
        elif instance.is_default:
            validated_data.pop("is_default", None)

        return super().update(instance, validated_data)
