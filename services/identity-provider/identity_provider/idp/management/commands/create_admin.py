"""
Idempotent admin bootstrap.

Reads IDP_ADMIN_USERNAME / IDP_ADMIN_PASSWORD / IDP_ADMIN_EMAIL from env.
If a user with that username already exists, leave it alone.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Idempotently bootstrap the IdP admin user from env vars."

    def handle(self, *args, **options):
        username = os.environ.get("IDP_ADMIN_USERNAME", "").strip()
        password = os.environ.get("IDP_ADMIN_PASSWORD", "")
        email = os.environ.get("IDP_ADMIN_EMAIL", "admin@example.com").strip()

        if not username or not password:
            self.stdout.write("IDP_ADMIN_USERNAME / IDP_ADMIN_PASSWORD not set, skipping")
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Admin '{username}' already exists, skipping")
            return

        user = User(
            username=username,
            email=email,
            role="ADMIN",
            is_staff=True,
            is_superuser=True,
        )
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Admin '{username}' created (sub={user.sub})"))
