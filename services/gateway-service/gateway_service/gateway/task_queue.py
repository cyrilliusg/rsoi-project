# Redis-backed async retry queue. Disabled: Redis is not deployed in k8s.
# The whole module is kept as a no-op so call sites (and the worker
# management command) continue to import cleanly.

# import json
# import time
import logging
from typing import Dict, Any
# import redis
# from django.conf import settings

logger = logging.getLogger(__name__)


# redis_client = redis.Redis.from_url(settings.REDIS_URL)
redis_client = None

QUEUE_KEY = "gateway:tasks"
RETRY_DELAY = 10  # секунд


def enqueue_task(task_type: str, payload: Dict[str, Any], retry: int = 0) -> None:
    logger.warning(
        "enqueue_task skipped (Redis disabled): type=%s payload=%s retry=%s",
        task_type, payload, retry,
    )
    # task = {
    #     "type": task_type,
    #     "payload": payload,
    #     "retry": retry,
    #     "ts": time.time(),
    # }
    # redis_client.rpush(QUEUE_KEY, json.dumps(task))
