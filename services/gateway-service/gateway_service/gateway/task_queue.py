import json
import time
import logging
from typing import Dict, Any
import redis
from django.conf import settings

logger = logging.getLogger(__name__)


redis_client = redis.Redis.from_url(settings.REDIS_URL)

QUEUE_KEY = "gateway:tasks"
RETRY_DELAY = 10  # секунд


def enqueue_task(task_type: str, payload: Dict[str, Any], retry: int = 0) -> None:
    task = {
        "type": task_type,
        "payload": payload,
        "retry": retry,
        "ts": time.time(),
    }
    redis_client.rpush(QUEUE_KEY, json.dumps(task))
    logger.info("Enqueued task %s: %s", task_type, payload)
