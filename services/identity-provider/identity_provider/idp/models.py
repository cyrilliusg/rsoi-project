"""
Identity Provider models.

Contract: docs/identity-provider.md.
"""
import secrets
import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Identity Provider user.

    `sub` is the stable identifier exposed in JWT, not the integer pk.
    `role` drives the IsAdmin permission across all services.
    """
    class Role(models.TextChoices):
        USER = "USER", "User"
        ADMIN = "ADMIN", "Admin"

    sub = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True, editable=False)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    email = models.EmailField(unique=True)

    class Meta:
        db_table = "idp_user"


class Client(models.Model):
    """OAuth client (frontend SPA, postman). Public clients have empty secret."""
    client_id = models.CharField(max_length=80, unique=True)
    client_secret_hash = models.CharField(max_length=255, blank=True, default="")
    redirect_uris = models.JSONField(default=list)
    scopes = models.JSONField(default=list)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "idp_client"

    def __str__(self) -> str:
        return f"Client({self.client_id})"

    def redirect_uri_allowed(self, redirect_uri: str) -> bool:
        return redirect_uri in (self.redirect_uris or [])


class AuthorizationCode(models.Model):
    """Short-lived (~60s) one-shot code for the authorization code flow."""
    DEFAULT_TTL_SECONDS = 60

    code = models.CharField(max_length=80, unique=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    redirect_uri = models.CharField(max_length=500)
    scope = models.CharField(max_length=500)
    code_challenge = models.CharField(max_length=255, blank=True, default="")
    code_challenge_method = models.CharField(max_length=10, blank=True, default="")
    expires_at = models.DateTimeField()
    consumed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "idp_authorization_code"
        indexes = [models.Index(fields=["consumed", "expires_at"])]

    @classmethod
    def issue(
        cls,
        *,
        user: "User",
        client: "Client",
        redirect_uri: str,
        scope: str,
        code_challenge: str,
        code_challenge_method: str,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> "AuthorizationCode":
        return cls.objects.create(
            code=secrets.token_urlsafe(32),
            user=user,
            client=client,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=timezone.now() + timedelta(seconds=ttl_seconds),
        )

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
