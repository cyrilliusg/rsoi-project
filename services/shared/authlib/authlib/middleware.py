"""
DRF authentication class.

Phase 0: skeleton. Phase 2 implements the full flow:
  1. Read Authorization: Bearer <jwt>
  2. Decode header → kid
  3. Get key from JWKSCache
  4. Verify signature, exp, iss, aud
  5. Build LightUser, return (user, token).

See ../../../docs/identity-provider.md for the JWT claim contract.
"""
from rest_framework.authentication import BaseAuthentication


class JWTAuthentication(BaseAuthentication):
    """Stub. Phase 2 will implement real validation."""

    def authenticate(self, request):
        raise NotImplementedError(
            "authlib.JWTAuthentication is a phase 0 skeleton. "
            "Implement in phase 2 of docs/plan.md."
        )
