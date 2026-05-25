"""
pytest configuration: minimal Django + DRF setup so we can import authlib.
We don't need a database — JWTAuthentication is DB-less.
"""
import django
from django.conf import settings


def pytest_configure():
    if not settings.configured:
        settings.configure(
            DEBUG=False,
            SECRET_KEY="test",
            IDP_ISSUER="http://idp.test",
            IDP_JWKS_URI="http://idp.test/api/v1/jwks",
            IDP_AUDIENCE="spa",
            IDP_JWKS_TTL=600,
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
                "rest_framework",
            ],
            DATABASES={
                "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"},
            },
            USE_TZ=True,
        )
        django.setup()
