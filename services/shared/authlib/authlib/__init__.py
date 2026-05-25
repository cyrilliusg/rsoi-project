"""
authlib — JWT validation utilities for rsoi-project Django services.

See ../README.md and ../../../docs/plan.md (Phase 2) for the public contract.
This module re-exports the public interface so downstream code can do:

    from authlib import LightUser, JWTAuthentication, IsAuthenticated, IsAdmin
"""
from .user import LightUser
from .jwks import JWKSCache
from .middleware import JWTAuthentication
from .permissions import IsAuthenticated, IsAdmin

__all__ = [
    "LightUser",
    "JWKSCache",
    "JWTAuthentication",
    "IsAuthenticated",
    "IsAdmin",
]

__version__ = "0.1.0"
