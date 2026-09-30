from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler

from core.responses import message_response


class MessageError(APIException):
    """Raise from anywhere in a view to return {"message": ..., **extra}."""

    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST, **extra):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.extra = extra


def exception_handler(exc, context):
    if isinstance(exc, MessageError):
        return message_response(exc.message, exc.status_code, **exc.extra)

    return drf_exception_handler(exc, context)
