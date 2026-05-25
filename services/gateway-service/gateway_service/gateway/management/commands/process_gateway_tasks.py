import json
import time
import logging

from django.core.management.base import BaseCommand
from ...task_queue import redis_client, QUEUE_KEY, RETRY_DELAY, enqueue_task
from ... import clients

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process async gateway tasks from Redis queue"
    TASK_HANDLERS = {
        "cancel_rental": clients.cancel_rental,
        "cancel_payment": clients.cancel_payment,
    }

    def handle(self, *args, **options):
        self.stdout.write("Starting gateway task worker...")
        while True:
            try:
                _, raw = redis_client.blpop(QUEUE_KEY)
            except Exception:
                logger.exception("Redis BLPOP failed, sleep 5s")
                time.sleep(5)
                continue

            try:
                task = json.loads(raw)
            except Exception:
                logger.exception("Failed to decode task: %r", raw)
                continue

            self._process_task(task)

    @staticmethod
    def _process_task(task: dict):
        task_type = task.get("type")
        payload = task.get("payload", {})
        retry = task.get("retry", 0)

        logger.info("Processing task %s (retry=%s): %s", task_type, retry, payload)

        try:
            handler = Command.TASK_HANDLERS.get(task_type)
            if handler:
                handler(**payload)
            else:
                logger.warning("Unknown task type: %s", task_type)
                return
        except Exception:
            logger.exception("Task %s failed, will retry", task_type)
            time.sleep(RETRY_DELAY)
            enqueue_task(task_type, payload, retry=retry + 1)
        else:
            logger.info("Task %s succeeded", task_type)
