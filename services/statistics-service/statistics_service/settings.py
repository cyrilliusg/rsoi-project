"""
Django settings for statistics_service project.

Consumes events from Kafka topic 'rental-events' (see docs/kafka-events.md)
and exposes an admin-only HTTP API for reports.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
MODE = os.environ['MODE']
ALLOWED_HOSTS = os.environ['DJANGO_ALLOWED_HOSTS'].split(',')

DB_NAME = os.environ['DB_STATISTICS']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_DOCKER_HOST = os.environ['DB_DOCKER_HOST']
DB_LOCAL_HOST = os.environ['DB_LOCAL_HOST']
DB_PORT = os.environ['DB_PORT']

# Kafka (used by phase 4 consumer command)
KAFKA_BOOTSTRAP = os.environ.get('KAFKA_BOOTSTRAP', 'kafka:9092')
KAFKA_TOPIC = os.environ.get('KAFKA_TOPIC', 'rental-events')
KAFKA_CONSUMER_GROUP = os.environ.get('KAFKA_CONSUMER_GROUP', 'statistics-service-cg')
KAFKA_AUTO_OFFSET_RESET = os.environ.get('KAFKA_AUTO_OFFSET_RESET', 'earliest')

# JWT validation (phase 2) — same env names as other services
IDP_ISSUER = os.environ.get('IDP_ISSUER', 'http://identity-provider:8000')
IDP_JWKS_URI = os.environ.get('IDP_JWKS_URI', f'{IDP_ISSUER}/api/v1/jwks')
IDP_AUDIENCE = os.environ.get('IDP_AUDIENCE', 'spa')

if MODE == 'local':
    DB_HOST = DB_LOCAL_HOST
    DEBUG = True
else:
    DB_HOST = DB_DOCKER_HOST
    DEBUG = False

STATIC_ROOT = BASE_DIR / "staticfiles"

ASGI_APPLICATION = "statistics_service.asgi.application"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
    }
}

if "test" in sys.argv:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "testdb.sqlite3"),
    }

# --------------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'statistics_service.stats.apps.StatsConfig',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'authlib.middleware.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'authlib.permissions.IsAuthenticated',
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'statistics_service.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'statistics_service.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
