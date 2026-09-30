import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shopping_backend.settings")

import django

django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

if email and password:

    user = User.objects.filter(email=email).first()

    if user:
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        print("Existing user promoted to superuser.")

    else:
        User.objects.create_superuser(
            email=email,
            password=password,
        )

        print("Superuser created successfully.")

else:
    print("Superuser environment variables are missing.")