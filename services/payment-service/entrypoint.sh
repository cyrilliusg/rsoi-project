#!/usr/bin/env sh

set -eu

python manage.py migrate --noinput

# Параметры
: "${WEB_CONCURRENCY:=3}"
: "${WEB_TIMEOUT:=120}"

# запускаем django из под appuser и пишем имя проекта
exec gosu appuser:appuser gunicorn payment_service.asgi:application \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers "${WEB_CONCURRENCY}" \
  --timeout "${WEB_TIMEOUT}" \
  --forwarded-allow-ips="*" # \
