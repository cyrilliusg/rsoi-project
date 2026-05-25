#!/usr/bin/env sh

set -eu


if [ "$ROLE" = "worker" ]; then
  echo "Starting gateway task worker..."
  exec gosu appuser:appuser python manage.py process_gateway_tasks

else
  echo "Starting web (gunicorn)..."
  python manage.py migrate --noinput

  # Параметры
  : "${WEB_CONCURRENCY:=3}"
  : "${WEB_TIMEOUT:=120}"

  # запускаем django из под appuser и пишем имя проекта
  exec gosu appuser:appuser gunicorn gateway_service.asgi:application \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --workers "${WEB_CONCURRENCY}" \
    --timeout "${WEB_TIMEOUT}" \
    --forwarded-allow-ips="*" # \
fi
