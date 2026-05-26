# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
      gosu \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip \
 && python -m pip wheel --wheel-dir=/wheels -r /tmp/requirements.txt \
 && python -m pip install --no-cache-dir /wheels/* \
 && rm -rf /wheels

# Shared authlib (JWT validation) — supplied via additional_contexts in compose
COPY --from=shared /authlib /shared/authlib
RUN pip install --no-cache-dir /shared/authlib

COPY . /app

RUN useradd --system --create-home --shell /usr/sbin/nologin appuser \
 && chown -R appuser:appuser /app

COPY --chown=appuser:appuser /entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8000

CMD ["/entrypoint.sh"]
