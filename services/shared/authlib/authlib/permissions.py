"""
DRF permission classes for use with authlib.JWTAuthentication.
"""
from rest_framework.permissions import BasePermission


class IsAuthenticated(BasePermission):
    message = "Authentication required."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(user and getattr(user, "is_authenticated", False))


class IsAdmin(BasePermission):
    message = "Admin role required."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and getattr(user, "role", None) == "ADMIN"
        )
