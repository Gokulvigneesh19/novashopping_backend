from django.db import transaction

from models import Address


def clear_default_address(user, exclude=None):
    """Unset the user's current default address (except `exclude`)."""
    addresses = Address.objects.filter(
        user=user,
        is_default=True
    )

    if exclude is not None:
        addresses = addresses.exclude(id=exclude.id)

    addresses.update(is_default=False)


@transaction.atomic
def delete_address(address):
    """Delete an address; if it was the default, promote the newest remaining one."""
    user = address.user
    was_default = address.is_default

    address.delete()

    if was_default:
        next_address = Address.objects.filter(
            user=user
        ).order_by("-created_at").first()

        if next_address:
            next_address.is_default = True
            next_address.save(update_fields=["is_default", "updated_at"])
