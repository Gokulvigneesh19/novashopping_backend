from rest_framework import status

from core.exceptions import MessageError


def get_object_or_error(queryset, message, **filters):
    """Like get_object_or_404, but responds with {"message": message}."""
    if hasattr(queryset, "objects"):
        queryset = queryset.objects.all()

    obj = queryset.filter(**filters).first()

    if obj is None:
        raise MessageError(message, status.HTTP_404_NOT_FOUND)

    return obj


def validate_or_error(serializer, message):
    """Validate, responding with {"message": message, "errors": ...} on failure."""
    if not serializer.is_valid():
        raise MessageError(message, errors=serializer.errors)


def get_error_message(errors):
    """Flatten DRF serializer.errors into the first concrete error string."""
    for value in errors.values():
        if isinstance(value, dict):
            return get_error_message(value)
        if isinstance(value, (list, tuple)) and value:
            return str(value[0])
        return str(value)
    return "Invalid data."
