"""
JWKS cache.

Phase 0: skeleton with public interface. Real fetch / TTL / kid → key mapping
lands in phase 2 (see ../../../docs/plan.md).
"""
from typing import Any


class JWKSCache:
    """In-memory cache of JWKs fetched from `jwks_uri`."""

    def __init__(self, jwks_uri: str, ttl: int = 600) -> None:
        self.jwks_uri = jwks_uri
        self.ttl = ttl
        self._cache: dict[str, Any] = {}
        self._fetched_at: float = 0.0

    def get_key(self, kid: str) -> Any:
        """Return public key (cryptography RSAPublicKey) for given kid.

        Raises KeyError if kid is not in cache after refetch.
        """
        raise NotImplementedError("Phase 2: implement JWKs fetch + cache.")
