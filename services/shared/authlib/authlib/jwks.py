"""
JWKS cache.

Fetches JWKs from the IdP and caches them in-memory with a TTL.
Refetches on miss (unknown `kid`) or after TTL expires.

Thread-safety: in-memory dict — fine for gunicorn sync/uvicorn workers,
each worker has its own cache. Multiple processes => multiple caches,
but JWKs only change on key rotation, so duplicate fetches are cheap.
"""
from __future__ import annotations

import base64
import logging
import threading
import time
from typing import Optional

import jwt
import requests
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

logger = logging.getLogger(__name__)


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _jwk_to_rsa_public_key(jwk: dict) -> RSAPublicKey:
    """Build an RSAPublicKey from a single JWK dict.

    Uses PyJWT's JWK algorithm — it handles the JWK → RSAPublicKey
    conversion correctly, including all the base64url padding quirks.
    """
    from jwt.algorithms import RSAAlgorithm
    return RSAAlgorithm.from_jwk(jwk)


class JWKSCache:
    """In-memory cache of JWKs fetched from `jwks_uri`."""

    def __init__(self, jwks_uri: str, ttl: int = 600, http_timeout: int = 5) -> None:
        self.jwks_uri = jwks_uri
        self.ttl = ttl
        self.http_timeout = http_timeout
        self._keys: dict[str, RSAPublicKey] = {}
        self._fetched_at: float = 0.0
        self._lock = threading.Lock()

    def _is_stale(self) -> bool:
        return (time.time() - self._fetched_at) > self.ttl

    def _refetch(self) -> None:
        logger.info("JWKSCache: fetching from %s", self.jwks_uri)
        resp = requests.get(self.jwks_uri, timeout=self.http_timeout)
        resp.raise_for_status()
        data = resp.json()
        new_keys: dict[str, RSAPublicKey] = {}
        for jwk in data.get("keys", []):
            kid = jwk.get("kid")
            if not kid:
                continue
            try:
                new_keys[kid] = _jwk_to_rsa_public_key(jwk)
            except Exception:
                logger.exception("JWKSCache: failed to parse jwk %s", kid)
        if not new_keys:
            raise RuntimeError(f"JWKS at {self.jwks_uri} returned no usable keys")
        self._keys = new_keys
        self._fetched_at = time.time()

    def get_key(self, kid: str) -> RSAPublicKey:
        """Return public key for `kid`.

        Refetches when cache is stale (TTL expired). Unknown `kid` from a
        fresh cache is treated as an unknown key (KeyError) — we don't
        refetch on every unknown kid because that would let any caller
        DoS the IdP by sending tokens with random kids.
        """
        with self._lock:
            if self._is_stale():
                self._refetch()
            if kid not in self._keys:
                raise KeyError(f"Unknown kid: {kid}")
            return self._keys[kid]

    # ---- Test hooks (used by unit tests; not part of public contract) ----

    def _inject(self, keys: dict[str, RSAPublicKey]) -> None:
        """Bypass HTTP fetch — for unit tests."""
        with self._lock:
            self._keys = dict(keys)
            self._fetched_at = time.time()
