from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from models import Cart, User, Wishlist


class SignupSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    confirm_password = serializers.CharField(
        write_only=True
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "phone_code",
            "email",
            "password",
            "confirm_password",
            
        ]
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Email already exists."
            )

        return value

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {
                    "password": "Passwords do not match."
                }
            )

        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")

        user = User.objects.create_user(
            email=validated_data["email"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            password=validated_data["password"],
            phone_number=validated_data.get("phone_number", ""),
            phone_code=validated_data.get("phone_code", ""),
        )

        refresh = RefreshToken.for_user(user)

        return {
             "refresh": str(refresh),
             "access": str(refresh.access_token),
             "user": user
        }


class LoginSerializer(serializers.Serializer):

    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True
    )

    def validate(self, data):

        email = data.get("email")
        password = data.get("password")

        user = authenticate(
            email=email,
            password=password
        )

        if user is None:
            raise serializers.ValidationError(
                "Invalid email or password."
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "This account is inactive."
            )

        refresh = RefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "phone_code": user.phone_code,
                "is_host": user.is_host,
            }
        }


class ProfileSerializer(serializers.ModelSerializer):
    wishlist_count = serializers.SerializerMethodField()
    cart_count = serializers.SerializerMethodField()

    def get_wishlist_count(self, obj):
        try:
            return obj.wishlist.items.count()
        except Wishlist.DoesNotExist:
            return 0

    def get_cart_count(self, obj):
        try:
            return obj.cart.items.count()
        except Cart.DoesNotExist:
            return 0
        
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone_number",
            "phone_code",
            "email",
            "is_host",
            "wishlist_count",
            "cart_count",
        ]

        # These fields cannot be changed through profile editing
        read_only_fields = [
            "id",
            "email",
            "is_host",
        ]        

class UserSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(source="date_joined", read_only=True)

    # Annotated by UserListView: delivered, paid orders and their total
    orders = serializers.IntegerField(source="completed_orders", read_only=True)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "phone_number",
            "phone_code",
            "email",
            "is_host",
            "orders",
            "total_spent",
            "created_at"
        ]
