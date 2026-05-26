"""
Kafka consumer for statistics-service.

Reads `rental-events` topic and persists each message in EventLog.
Idempotent by `eventId` (UNIQUE constraint + get_or_create).

Run via:  python manage.py run_consumer
Container: services/statistics-service/entrypoint.sh switches on ROLE=consumer.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from ...models import EventLog

logger = logging.getLogger(__name__)


def _parse_event(raw: bytes) -> dict | None:
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        logger.exception("Bad event payload: %r", raw[:200])
        return None


def _persist(event: dict) -> bool:
    """Write a single event to EventLog. Returns True if newly inserted."""
    event_id = event.get("eventId")
    if not event_id:
        logger.warning("Event without eventId, skipping: %s", event)
        return False
    ts_raw = event.get("timestamp")
    ts = parse_datetime(ts_raw) if ts_raw else datetime.utcnow()
    _, created = EventLog.objects.update_or_create(
        event_id=event_id,
        defaults={
            "event_type": event.get("eventType", ""),
            "timestamp": ts,
            "user_id": event.get("userId") or "00000000-0000-0000-0000-000000000000",
            "username": event.get("username", "") or "",
            "correlation_id": event.get("correlationId", "") or "",
            "payload": event.get("data") or {},
        },
    )
    return created


class Command(BaseCommand):
    help = "Consume rental-events from Kafka and write to EventLog"

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process available messages and exit (for tests).",
        )

    def handle(self, *args, **options):
        # Import kafka lazily so that the rest of the project can import this
        # module (e.g. for `manage.py check`) without kafka-python installed.
        from kafka import KafkaConsumer

        bootstrap = settings.KAFKA_BOOTSTRAP.split(",")
        topic = settings.KAFKA_TOPIC
        group = settings.KAFKA_CONSUMER_GROUP
        offset_reset = settings.KAFKA_AUTO_OFFSET_RESET

        self.stdout.write(self.style.SUCCESS(
            f"Starting consumer on {bootstrap} topic={topic} group={group}"
        ))

        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap,
            group_id=group,
            auto_offset_reset=offset_reset,
            enable_auto_commit=True,
            value_deserializer=lambda v: v,
        )

        try:
            if options.get("once"):
                for msg in consumer.poll(timeout_ms=2000).values():
                    for rec in msg:
                        event = _parse_event(rec.value)
                        if event is not None:
                            _persist(event)
                return

            for rec in consumer:
                event = _parse_event(rec.value)
                if event is None:
                    continue
                try:
                    created = _persist(event)
                    if created:
                        logger.info("Stored %s corr=%s", event.get("eventType"), event.get("correlationId"))
                    else:
                        logger.debug("Duplicate event %s ignored", event.get("eventId"))
                except Exception:
                    logger.exception("Failed to persist event %s", event.get("eventId"))
                    # Don't crash the consumer — at-least-once delivery is fine,
                    # but we shouldn't break the loop on transient DB errors.
                    time.sleep(1)
        finally:
            try:
                consumer.close()
            except Exception:
                pass
