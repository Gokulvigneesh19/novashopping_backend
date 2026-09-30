from django.db import migrations


ADDRESS_FIELDS = ["address", "city", "state", "country", "postal_code"]


def copy_profile_addresses(apps, schema_editor):
    """Save each user's profile address as their default Address before the columns are dropped."""
    User = apps.get_model("users", "User")
    Address = apps.get_model("address", "Address")

    for user in User.objects.all():
        if not any(getattr(user, field) for field in ADDRESS_FIELDS):
            continue

        if Address.objects.filter(user=user).exists():
            continue

        Address.objects.create(
            user=user,
            name=f"{user.first_name} {user.last_name}".strip() or user.email,
            phone=user.phone_number or "",
            address=user.address or "",
            city=user.city or "",
            state=user.state or "",
            postal_code=user.postal_code or "",
            country=user.country or "India",
            is_default=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_user_postal_code"),
        ("address", "0002_single_address_field"),
    ]

    operations = [
        migrations.RunPython(copy_profile_addresses, migrations.RunPython.noop),
        migrations.RemoveField(model_name="user", name="address"),
        migrations.RemoveField(model_name="user", name="city"),
        migrations.RemoveField(model_name="user", name="state"),
        migrations.RemoveField(model_name="user", name="country"),
        migrations.RemoveField(model_name="user", name="postal_code"),
    ]
