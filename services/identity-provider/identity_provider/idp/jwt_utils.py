"""
JWT encode/decode using the IdP's RSA keypair.

Contract: docs/identity-provider.md §JWT.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone as dt_tz
from typing import Optional

import jwt
from django.conf import settings

from .keys import get_keypair
from .models import User


def build_claims(
    *,
    user: User,
    client_id: str,
    scope: str,
    ttl_seconds: Optional[int] = None,
) -> dict:
    """Build the JWT payload for a given user + scope."""
    now = datetime.now(dt_tz.utc)
    ttl = ttl_seconds if ttl_seconds is not None else settings.IDP_ACCESS_TOKEN_TTL
    scopes = set(scope.split())

    claims: dict = {
        "iss": settings.IDP_ISSUER,
        "sub": str(user.sub),
        "aud": client_id,
        "azp": client_id,
        "exp": int(now.timestamp()) + int(ttl),
        "iat": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "scope": " ".join(sorted(scopes)),
        "preferred_username": user.username,
        "role": user.role,
    }
    if "profile" in scopes:
        full_name = " ".join(p for p in (user.first_name, user.last_name) if p)
        claims["name"] = full_name or user.username
    if "email" in scopes and user.email:
        claims["email"] = user.email
    return claims


def encode(claims: dict) -> str:
    kp = get_keypair()
    return jwt.encode(
        payload=claims,
        key=kp.private_pem,
        algorithm="RS256",
        headers={"kid": kp.kid, "typ": "JWT"},
    )


def issue_token(*, user: User, client_id: str, scope: str) -> tuple[str, dict]:
    """Issue a signed JWT for the user + scope. Returns (token, claims)."""
    claims = build_claims(user=user, client_id=client_id, scope=scope)
    return encode(claims), claims
