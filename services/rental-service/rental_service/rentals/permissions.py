from rest_framework.permissions import BasePermission

class HasUserHeader(BasePermission):
    message = "Требуется заголовок X-User-Name."

    def has_permission(self, request, view):
        return bool(request.headers.get("X-User-Name"))
