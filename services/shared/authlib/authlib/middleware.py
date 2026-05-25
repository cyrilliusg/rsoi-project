"""
DRF authentication class — validates RS256 JWTs against IdP JWKs.

Configuration (Django settings):
    IDP_ISSUER           required, e.g. "http://identity-provider:8000"
    IDP_JWKS_URI         optional, default f"{IDP_ISSUER}/api/v1/jwks"
    IDP_AUDIENCE         CSV of allowed audiences, e.g. "spa" or "spa,postman"
    IDP_JWKS_TTL         optional, default 600 seconds

On success, request.user becomes a LightUser. On failure, raises
AuthenticationFailed (DRF turns this into 401 because authenticate_header
returns "Bearer").
"""
from __future__ import annotations

import logging
import threading

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions

from .jwks import JWKSCache
from .user import LightUser

logger = logging.getLogger(__name__)


_cache_lock = threading.Lock()
_cache: JWKSCache | None = None


def _reset_cache_for_tests() -> None:
    """Force the next authenticate() call to rebuild the cache from settings."""
    global _cache
    with _cache_lock:
        _cache = None


def _get_cache() -> JWKSCache:
    """Lazily build a single per-process JWKSCache."""
    global _cache
    if _cache is None:
        with _cache_lock:
            if _cache is None:
                issuer = getattr(settings, "IDP_ISSUER", None)
                if not issuer:
                    raise RuntimeError("IDP_ISSUER setting is required for authlib.")
                jwks_uri = getattr(settings, "IDP_JWKS_URI", None) or f"{issuer.rstrip('/')}/api/v1/jwks"
                ttl = int(getattr(settings, "IDP_JWKS_TTL", 600))
                _cache = JWKSCache(jwks_uri=jwks_uri, ttl=ttl)
    return _cache


def _allowed_audiences() -> list[str]:
    aud = getattr(settings, "IDP_AUDIENCE", "")
    if isinstance(aud, str):
        return [a.strip() for a in aud.split(",") if a.strip()]
    return list(aud) if aud else []


class JWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate_header(self, request):
        # Ensures DRF returns 401 (with WWW-Authenticate) on failed/missing auth.
        return self.keyword

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header.startswith(self.keyword + " "):
            return None
        token = header[len(self.keyword) + 1 :].strip()
        if not token:
            return None

        try:
            unverified_header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed(f"Invalid token header: {exc}")

        kid = unverified_header.get("kid")
        if not kid:
            raise exceptions.AuthenticationFailed("JWT header missing kid")

        try:
            public_key = _get_cache().get_key(kid)
        except KeyError:
            raise exceptions.AuthenticationFailed("Unknown signing key (kid)")
        except Exception as exc:
            logger.exception("Failed to fetch JWKs")
            raise exceptions.AuthenticationFailed(f"Cannot verify token: {exc}")

        issuer = getattr(settings, "IDP_ISSUER", None)
        audiences = _allowed_audiences()

        decode_kwargs: dict = {
            "key": public_key,
            "algorithms": ["RS256"],
            "issuer": issuer,
            "options": {"require": ["exp", "iat", "iss", "sub"]},
        }
        if audiences:
            decode_kwargs["audience"] = audiences

        try:
            claims = jwt.decode(token, **decode_kwargs)
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token expired")
        except jwt.InvalidIssuerError:
            raise exceptions.AuthenticationFailed("Invalid issuer")
        except jwt.InvalidAudienceError:
            raise exceptions.AuthenticationFailed("Invalid audience")
        except jwt.InvalidTokenError as exc:
            raise exceptions.AuthenticationFailed(f"Invalid token: {exc}")

        scope = (claims.get("scope") or "").split()
        user = LightUser(
            sub=str(claims["sub"]),
            username=claims.get("preferred_username", ""),
            role=claims.get("role", "USER"),
            email=claims.get("email"),
            name=claims.get("name"),
            scope=scope,
        )
        request.jwt_claims = claims
        request.jwt_scope = set(scope)
        return user, token
