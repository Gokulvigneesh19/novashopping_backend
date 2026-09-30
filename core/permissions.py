from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated


class IsHost(BasePermission):
    message = "Only hosts are allowed to perform this action."

    def has_permission(self, request, view):

        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_host


class PublicReadHostWriteMixin:
    """Anyone can GET; every other method needs an authenticated host."""

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]

        return [IsAuthenticated(), IsHost()]
