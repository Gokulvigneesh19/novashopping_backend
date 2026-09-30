from rest_framework import status
from rest_framework.response import Response


def message_response(message, status_code=status.HTTP_200_OK, **data):
    """Envelope used by most endpoints: {"message": ..., **data}."""
    return Response(
        {
            "message": message,
            **data
        },
        status=status_code
    )


def status_response(success, message, status_code=status.HTTP_200_OK, **data):
    """Envelope used by the user endpoints: {"status", "message", "statusCode", **data}."""
    return Response(
        {
            "status": success,
            "message": message,
            "statusCode": status_code,
            **data
        },
        status=status_code
    )
