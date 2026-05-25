#!/usr/bin/env sh

set -eu

if [ "${ROLE:-web}" = "consumer" ]; then
  echo "Starting Kafka consumer for statistics-service..."
  exec gosu appuser:appuser python manage.py run_consumer

else
  echo "Starting web (gunicorn)..."
  python manage.py migrate --noinput

  : "${WEB_CONCURRENCY:=3}"
  : "${WEB_TIMEOUT:=120}"

  exec gosu appuser:appuser gunicorn statistics_service.asgi:application \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --workers "${WEB_CONCURRENCY}" \
    --timeout "${WEB_TIMEOUT}" \
    --forwarded-allow-ips="*"
fi
