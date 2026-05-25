# authlib

Shared Python package: validates RS256 JWTs issued by `identity-provider` against its JWKs endpoint, caches the keys in memory, exposes a DRF `BaseAuthentication` and `BasePermission` classes.

Implementation lands in **Phase 2** of [../../../docs/plan.md](../../../docs/plan.md). This is the phase-0 skeleton — only public interfaces are pinned.

## Usage (after phase 2)

In a Django service `settings.py`:

```python
INSTALLED_APPS = [..., "authlib"]   # optional, package has no app config currently

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["authlib.middleware.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["authlib.permissions.IsAuthenticated"],
}

# Required env (read by authlib at import time / lazily):
# IDP_ISSUER, IDP_JWKS_URI, IDP_AUDIENCE
```

In Dockerfile of a backend service:

```dockerfile
COPY ../shared/authlib /shared/authlib
RUN pip install -e /shared/authlib
```

(Actual mount technique TBD in phase 2 — context paths may force us to keep `shared/` inside each service's build context. See [docs/plan.md](../../../docs/plan.md) §6 "Shared authlib".)

## Public interface (frozen contract)

### `authlib.middleware.JWTAuthentication`

DRF `BaseAuthentication` subclass. On success, `request.user` becomes a `LightUser` dataclass.

### `authlib.jwks.JWKSCache`

In-memory cache with TTL. Refetches from `jwks_uri` on miss or after TTL expires.

### `authlib.permissions.IsAuthenticated` / `IsAdmin`

DRF `BasePermission` subclasses.

### `authlib.LightUser`

```python
@dataclass(frozen=True)
class LightUser:
    sub: str          # JWT 'sub' (UUID string)
    username: str     # 'preferred_username'
    email: str | None
    name: str | None
    role: str         # 'USER' | 'ADMIN'
    scope: list[str]
    is_authenticated: bool = True
```
