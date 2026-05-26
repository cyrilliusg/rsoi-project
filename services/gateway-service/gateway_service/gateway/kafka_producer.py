"""
Kafka producer for gateway-service.

Single per-process producer (kafka-python uses its own background thread
for the actual send, so .send() is non-blocking). We never call flush()
on the hot path — failures get logged via the errback.

Schema contract: docs/kafka-events.md.
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone as dt_tz
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

_producer_lock = threading.Lock()
_producer: Optional[object] = None  # actually KafkaProducer | None


def _get_producer():
    global _producer
    if _producer is not None:
        return _producer
    with _producer_lock:
        if _producer is not None:
            return _producer
        bootstrap = getattr(settings, "KAFKA_BOOTSTRAP", "")
        if not bootstrap:
            return None
        try:
            from kafka import KafkaProducer  # imported lazily
            _producer = KafkaProducer(
                bootstrap_servers=bootstrap.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=5,
                client_id=getattr(settings, "KAFKA_CLIENT_ID", "gateway-service"),
                request_timeout_ms=10000,
                max_block_ms=2000,
            )
            logger.info("Kafka producer initialized (bootstrap=%s)", bootstrap)
        except Exception:
            logger.exception("Failed to init Kafka producer")
            _producer = None
    return _producer


def _on_send_error(exc):
    logger.warning("Kafka send failed: %r", exc)


def emit_event(
    event_type: str,
    *,
    user_id: str,
    username: str,
    correlation_id: str,
    data: dict,
) -> None:
    """Best-effort: log + send. Never raises into the caller.

    If Kafka is down we lose the event — acceptable for this learning
    project (see docs/known-issues.md / kafka-events.md "Producer" section).
    """
    producer = _get_producer()
    if producer is None:
        logger.warning("Kafka unavailable, skipping event %s (corr=%s)", event_type, correlation_id)
        return
    topic = getattr(settings, "KAFKA_TOPIC", "rental-events")
    payload = {
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "timestamp": datetime.now(dt_tz.utc).isoformat(),
        "userId": user_id,
        "username": username,
        "correlationId": correlation_id,
        "data": data,
    }
    try:
        future = producer.send(topic, key=user_id or None, value=payload)
        future.add_errback(_on_send_error)
        logger.info("Emitted %s corr=%s", event_type, correlation_id)
    except Exception:
        logger.exception("Failed to enqueue event %s", event_type)
