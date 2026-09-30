import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            email=email,
            password=password,
            **extra_fields
        )


class User(AbstractUser):

    username = None
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)

    email = models.EmailField(unique=True)

    # The shop owner: logs in through /api/admin/login/ and sees every order.
    # Only one user can be the host (enforced below).
    is_host = models.BooleanField(default=False)

    phone_number = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    phone_code = models.CharField(
        max_length=10,
        blank=True,
        null=True
    )
    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta(AbstractUser.Meta):
        app_label = "users"
        constraints = [
            models.UniqueConstraint(
                fields=["is_host"],
                condition=models.Q(is_host=True),
                name="only_one_host"
            )
        ]

    def __str__(self):
        return self.email
