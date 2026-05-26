"""
EventLog — single table of raw events ingested from Kafka.

Contract: docs/kafka-events.md §EventLog.
Aggregates are computed on-the-fly via SQL in stats.views (no materialized
tables yet — add when the table gets large).
"""
from django.db import models


class EventLog(models.Model):
    event_id = models.UUIDField(unique=True, db_index=True)
    event_type = models.CharField(max_length=80, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    user_id = models.UUIDField(db_index=True)
    username = models.CharField(max_length=80, blank=True, default="")
    correlation_id = models.CharField(max_length=80, blank=True, default="", db_index=True)
    payload = models.JSONField(default=dict)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "eventlog"
        ordering = ("-timestamp",)

    def __str__(self) -> str:
        return f"{self.event_type} {self.event_id}"
