# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# gosu для смены пользователя и ca-certificates для https-запросов
RUN apt-get update && apt-get install -y --no-install-recommends \
      gosu \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Установка python-зависимостей
COPY requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip \
 && python -m pip wheel --wheel-dir=/wheels -r /tmp/requirements.txt \
 && python -m pip install --no-cache-dir /wheels/* \
 && rm -rf /wheels

# Копируем проект
COPY . /app

# Создаем пользователя
RUN useradd --system --create-home --shell /usr/sbin/nologin appuser \
 && chown -R appuser:appuser /app
# USER appuser

# Копируем скрипт запуска и даём права
COPY --chown=appuser:appuser /entrypoint.sh /entrypoint.sh
# Удаляем CRLF, иначе /usr/bin/env видит 'sh\r'
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# Порт открываем
EXPOSE 8000

# HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
#   CMD python -c 'import urllib.request; urllib.request.urlopen("http://localhost:8000/health").read()' || exit 1

CMD ["/entrypoint.sh"]
