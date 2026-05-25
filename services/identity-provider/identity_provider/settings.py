"""
Django settings for identity_provider project.

See [docs/identity-provider.md](../../docs/identity-provider.md) for the public
contract this service implements.
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

DB_NAME = os.environ['DB_IDENTITY']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
DB_DOCKER_HOST = os.environ['DB_DOCKER_HOST']
DB_LOCAL_HOST = os.environ['DB_LOCAL_HOST']
DB_PORT = os.environ['DB_PORT']

# IdP-specific runtime config (used in phase 1+)
IDP_ISSUER = os.environ.get('IDP_ISSUER', 'http://localhost:8090')
IDP_ACCESS_TOKEN_TTL = int(os.environ.get('IDP_ACCESS_TOKEN_TTL', '3600'))
JWT_PRIVATE_KEY_PATH = os.environ.get('JWT_PRIVATE_KEY_PATH', '')
JWT_PRIVATE_KEY = os.environ.get('JWT_PRIVATE_KEY', '')
JWT_PUBLIC_KEY_PATH = os.environ.get('JWT_PUBLIC_KEY_PATH', '')
JWT_PUBLIC_KEY = os.environ.get('JWT_PUBLIC_KEY', '')

# Если запускаем локально, то соответствующий хост
if MODE == 'local':
    DB_HOST = DB_LOCAL_HOST
    DEBUG = True
else:
    DB_HOST = DB_DOCKER_HOST
    DEBUG = False

STATIC_ROOT = BASE_DIR / "staticfiles"

ASGI_APPLICATION = "identity_provider.asgi.application"

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

if "test" in sys.argv:  # manage.py test
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

    'corsheaders',
    'rest_framework',
    'identity_provider.idp.apps.IdpConfig',
]

AUTH_USER_MODEL = 'idp.User'

CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get('IDP_CORS_ORIGINS', '').split(',') if o.strip()
]
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
    ],
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'identity_provider.urls'

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

WSGI_APPLICATION = 'identity_provider.wsgi.application'

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
