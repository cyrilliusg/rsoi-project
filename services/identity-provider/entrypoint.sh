#!/usr/bin/env sh

set -eu

python manage.py migrate --noinput

# Bootstrap admin (idempotent: skips if user already exists)
python manage.py create_admin

# Register SPA client (idempotent; reads URIs from env or default)
SPA_REDIRECTS="${SPA_REDIRECT_URIS:-http://localhost:3000/auth/callback}"
SPA_REDIRECT_ARGS=""
for uri in $(echo "$SPA_REDIRECTS" | tr ',' ' '); do
  SPA_REDIRECT_ARGS="$SPA_REDIRECT_ARGS --redirect-uri $uri"
done
# shellcheck disable=SC2086
python manage.py create_client --client-id spa --public $SPA_REDIRECT_ARGS \
  --scope openid --scope profile --scope email

: "${WEB_CONCURRENCY:=3}"
: "${WEB_TIMEOUT:=120}"

exec gosu appuser:appuser gunicorn identity_provider.asgi:application \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers "${WEB_CONCURRENCY}" \
  --timeout "${WEB_TIMEOUT}" \
  --forwarded-allow-ips="*"
