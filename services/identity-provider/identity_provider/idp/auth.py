"""
Local JWT authentication for IdP-protected endpoints (userinfo, users).

In phase 2 the same logic will move into `shared/authlib` and be reused
across all services. IdP itself keeps a local copy so it can run
standalone.
"""
from __future__ import annotations

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions, permissions

from .keys import get_keypair
from .models import User


class JWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate_header(self, request):
        # Ensures DRF returns 401 (with WWW-Authenticate) instead of 403
        # when authentication fails or is absent.
        return self.keyword

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith(self.keyword + " "):
            return None
        token = header[len(self.keyword) + 1 :].strip()

        kp = get_keypair()
        try:
            claims = jwt.decode(
                token,
                key=kp.public_pem,
                algorithms=["RS256"],
                issuer=settings.IDP_ISSUER,
                options={"require": ["exp", "iat", "iss", "sub"], "verify_aud": False},
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token expired")
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed(f"Invalid token: {exc}")

        try:
            user = User.objects.get(sub=claims["sub"])
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed("User not found")

        request.jwt_claims = claims
        request.jwt_scope = set((claims.get("scope") or "").split())
        return user, token


class IsAdmin(permissions.BasePermission):
    message = "Admin role required."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and getattr(user, "role", None) == "ADMIN"
        )
