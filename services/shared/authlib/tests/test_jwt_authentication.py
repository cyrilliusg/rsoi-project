"""
Unit tests for authlib.middleware.JWTAuthentication.

The IdP is not running during these tests — we inject a known RSA key
pair into JWKSCache and sign tokens locally.
"""
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import RequestFactory
from rest_framework.exceptions import AuthenticationFailed

from authlib import JWTAuthentication, LightUser
from authlib.middleware import _get_cache, _reset_cache_for_tests


@pytest.fixture(autouse=True)
def reset_cache():
    _reset_cache_for_tests()
    yield
    _reset_cache_for_tests()


@pytest.fixture(scope="module")
def keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = priv.public_key()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return priv, pub, priv_pem


@pytest.fixture
def signed_token(keypair):
    """Factory: produces a signed JWT with given claim overrides."""
    _priv, _pub, priv_pem = keypair

    def _make(**overrides):
        now = int(time.time())
        claims = {
            "iss": "http://idp.test",
            "sub": str(uuid.uuid4()),
            "aud": "spa",
            "azp": "spa",
            "exp": now + 3600,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "scope": "openid profile email",
            "preferred_username": "kirill",
            "role": "USER",
            "name": "Kirill Ivanov",
            "email": "kirill@example.com",
        }
        claims.update(overrides)
        return jwt.encode(claims, priv_pem, algorithm="RS256", headers={"kid": "test-kid"})

    return _make


@pytest.fixture
def authed_cache(keypair):
    """Inject the test public key into the module-level JWKSCache."""
    _priv, pub, _priv_pem = keypair
    cache = _get_cache()
    cache._inject({"test-kid": pub})
    return cache


@pytest.fixture
def factory():
    return RequestFactory()


def _auth(factory, token):
    request = factory.get("/api/v1/cars", HTTP_AUTHORIZATION=f"Bearer {token}")
    return JWTAuthentication().authenticate(request)


def test_valid_token_returns_light_user(authed_cache, signed_token, factory):
    user, _token = _auth(factory, signed_token())
    assert isinstance(user, LightUser)
    assert user.username == "kirill"
    assert user.role == "USER"
    assert user.email == "kirill@example.com"
    assert user.is_authenticated is True


def test_admin_role_propagates(authed_cache, signed_token, factory):
    user, _ = _auth(factory, signed_token(role="ADMIN"))
    assert user.is_admin is True


def test_no_authorization_header_returns_none(factory):
    request = factory.get("/api/v1/cars")
    assert JWTAuthentication().authenticate(request) is None


def test_non_bearer_scheme_returns_none(factory):
    request = factory.get("/api/v1/cars", HTTP_AUTHORIZATION="Basic abcdef")
    assert JWTAuthentication().authenticate(request) is None


def test_expired_token_raises(authed_cache, signed_token, factory):
    expired = signed_token(exp=int(time.time()) - 60, iat=int(time.time()) - 3600)
    with pytest.raises(AuthenticationFailed) as exc:
        _auth(factory, expired)
    assert "expired" in str(exc.value).lower()


def test_wrong_issuer_rejected(authed_cache, signed_token, factory):
    token = signed_token(iss="http://evil.test")
    with pytest.raises(AuthenticationFailed) as exc:
        _auth(factory, token)
    assert "issuer" in str(exc.value).lower()


def test_wrong_audience_rejected(authed_cache, signed_token, factory):
    token = signed_token(aud="someone-else")
    with pytest.raises(AuthenticationFailed) as exc:
        _auth(factory, token)
    assert "audience" in str(exc.value).lower()


def test_unknown_kid_rejected(keypair, signed_token, factory):
    # Inject a *different* key than the one we sign with.
    other_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cache = _get_cache()
    cache._inject({"other-kid": other_priv.public_key()})
    with pytest.raises(AuthenticationFailed) as exc:
        _auth(factory, signed_token())
    # Either "Unknown signing key" or "Unknown kid"
    assert "kid" in str(exc.value).lower() or "key" in str(exc.value).lower()


def test_tampered_signature_rejected(keypair, signed_token, factory):
    # Inject a *different* key — the signature won't verify against it.
    other_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cache = _get_cache()
    cache._inject({"test-kid": other_priv.public_key()})
    with pytest.raises(AuthenticationFailed) as exc:
        _auth(factory, signed_token())
    assert "invalid" in str(exc.value).lower() or "signature" in str(exc.value).lower()


def test_missing_kid_header_rejected(keypair, factory):
    _priv, _pub, priv_pem = keypair
    token = jwt.encode(
        {
            "iss": "http://idp.test", "sub": "x", "aud": "spa",
            "exp": int(time.time()) + 3600, "iat": int(time.time()),
            "scope": "openid", "preferred_username": "x", "role": "USER",
        },
        priv_pem, algorithm="RS256",
    )
    with pytest.raises(AuthenticationFailed) as exc:
        _auth(factory, token)
    assert "kid" in str(exc.value).lower()
