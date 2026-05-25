"""
Kafka consumer entrypoint for statistics-service.

Phase 0: skeleton only. Real implementation lands in phase 4 of
docs/plan.md. The container with ROLE=consumer calls this command
via entrypoint.sh.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Consume events from Kafka topic and write to EventLog (phase 4)"

    def handle(self, *args, **options):
        self.stdout.write(
            "run_consumer is a phase 0 skeleton — implement in phase 4 "
            "(see docs/plan.md and docs/kafka-events.md)."
        )
