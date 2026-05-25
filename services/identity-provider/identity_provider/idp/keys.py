"""
RSA key loading + JWKs export.

The private key is loaded from either:
  - JWT_PRIVATE_KEY_PATH (file path), or
  - JWT_PRIVATE_KEY     (full PEM contents as env value).

The public key is derived from the private key — no need to provide it
separately. We expose JWT_PUBLIC_KEY_PATH / JWT_PUBLIC_KEY for the case
where a deployment wants to mount only the public half on read-only nodes
(not used in MVP).

`kid` is `sha256(DER public key)[:16]` (hex) — stable across restarts.
"""
from __future__ import annotations

import base64
import functools
import hashlib
from dataclasses import dataclass

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings


@dataclass(frozen=True)
class KeyPair:
    private_key: rsa.RSAPrivateKey
    public_key: rsa.RSAPublicKey
    private_pem: bytes
    public_pem: bytes
    kid: str


def _load_pem_bytes() -> bytes:
    """Return the PEM-encoded private key as bytes."""
    path = getattr(settings, "JWT_PRIVATE_KEY_PATH", "") or ""
    if path:
        with open(path, "rb") as f:
            return f.read()
    inline = getattr(settings, "JWT_PRIVATE_KEY", "") or ""
    if inline:
        return inline.encode("utf-8")
    raise RuntimeError(
        "No RSA private key configured. Set JWT_PRIVATE_KEY_PATH or JWT_PRIVATE_KEY."
    )


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _kid_for(public_der: bytes) -> str:
    return hashlib.sha256(public_der).hexdigest()[:16]


@functools.lru_cache(maxsize=1)
def get_keypair() -> KeyPair:
    """Loaded once per process. Cache invalidates on restart."""
    private_pem = _load_pem_bytes()
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise RuntimeError("Configured JWT key is not an RSA private key.")
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return KeyPair(
        private_key=private_key,
        public_key=public_key,
        private_pem=private_pem,
        public_pem=public_pem,
        kid=_kid_for(public_der),
    )


def jwks() -> dict:
    """Return JWKs document with the single current public key."""
    kp = get_keypair()
    numbers = kp.public_key.public_numbers()
    n_bytes = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
    e_bytes = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": kp.kid,
                "n": _b64url(n_bytes),
                "e": _b64url(e_bytes),
            }
        ]
    }
