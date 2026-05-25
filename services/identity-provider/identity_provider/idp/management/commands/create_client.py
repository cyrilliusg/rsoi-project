"""
Idempotent OAuth client registration.

Usage:
  python manage.py create_client \
      --client-id spa \
      --redirect-uri http://localhost:3000/auth/callback \
      --redirect-uri https://app.example/auth/callback \
      --scope openid --scope profile --scope email \
      --public

If a client with that client_id already exists, redirect_uris and scopes
are merged (idempotent add).
"""
from django.core.management.base import BaseCommand

from identity_provider.idp.models import Client


class Command(BaseCommand):
    help = "Idempotently register / update an OAuth client."

    def add_arguments(self, parser):
        parser.add_argument("--client-id", required=True)
        parser.add_argument("--redirect-uri", action="append", default=[], dest="redirect_uris")
        parser.add_argument("--scope", action="append", default=[], dest="scopes")
        parser.add_argument("--public", action="store_true", default=False)

    def handle(self, *args, **options):
        client_id = options["client_id"]
        redirect_uris = options["redirect_uris"]
        scopes = options["scopes"] or ["openid", "profile", "email"]
        is_public = options["public"]

        client, created = Client.objects.get_or_create(
            client_id=client_id,
            defaults={
                "redirect_uris": list(redirect_uris),
                "scopes": scopes,
                "is_public": is_public,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(
                f"Client '{client_id}' created with {len(redirect_uris)} redirect_uris"
            ))
            return

        # Idempotent merge
        existing_uris = set(client.redirect_uris or [])
        new_uris = sorted(existing_uris | set(redirect_uris))
        existing_scopes = set(client.scopes or [])
        new_scopes = sorted(existing_scopes | set(scopes))
        client.redirect_uris = new_uris
        client.scopes = new_scopes
        client.is_public = is_public
        client.save()
        self.stdout.write(self.style.SUCCESS(
            f"Client '{client_id}' updated: redirect_uris={new_uris}, scopes={new_scopes}"
        ))
