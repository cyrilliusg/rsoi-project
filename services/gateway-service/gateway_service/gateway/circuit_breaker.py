import time
import logging
from typing import Callable, TypeVar, Optional

logger = logging.getLogger(__name__)
T = TypeVar("T")


class ServiceUnavailable(Exception):
    """Исключение, когда сервис недоступен и нет/не нужен фолбэк."""
    pass


class CircuitBreaker:
    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout: int = 10):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = self.STATE_CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def _open(self):
        """Переводим в OPEN: дальше запросы не ходят какое-то время."""
        self.state = self.STATE_OPEN
        self.last_failure_time = time.time()
        logger.warning("CircuitBreaker[%s] OPEN", self.name)

    def _reset(self):
        """Полный сброс в CLOSED."""
        self.state = self.STATE_CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def _record_success(self):
        """На успехе всегда сбрасываемся в CLOSED."""
        if self.state != self.STATE_CLOSED:
            logger.info("CircuitBreaker[%s] SUCCESS -> CLOSED", self.name)
        self._reset()

    def _record_failure(self):
        """Обработка неуспеха в зависимости от текущего состояния."""
        now = time.time()

        if self.state == self.STATE_HALF_OPEN:
            # Пробная попытка провалилась — обратно в OPEN и ждём
            logger.warning("CircuitBreaker[%s] HALF_OPEN failure -> OPEN", self.name)
            self.state = self.STATE_OPEN
            self.failure_count = self.failure_threshold  # логически: достигли порога
            self.last_failure_time = now
            return

        # CLOSED или (теоретически) OPEN
        self.failure_count += 1
        self.last_failure_time = now

        logger.warning("CircuitBreaker[%s] failure count=%d", self.name, self.failure_count)

        if self.failure_count >= self.failure_threshold:
            self._open()

    def _can_try_call(self) -> bool:
        """
        Решаем, можно ли идти во внешний сервис:
        - CLOSED: всегда можно
        - OPEN: можно только если вышли из таймаута → переводим в HALF_OPEN
        - HALF_OPEN: можно (но это будет пробная попытка)
        """
        now = time.time()

        if self.state == self.STATE_OPEN:
            if now - self.last_failure_time >= self.recovery_timeout:
                # Разрешаем пробную попытку
                self.state = self.STATE_HALF_OPEN
                logger.info("CircuitBreaker[%s] timeout passed -> HALF_OPEN", self.name)
                return True
            else:
                return False

        # CLOSED или HALF_OPEN
        return True

    def call(
        self,
        func: Callable[..., T],
        *args,
        fallback: Optional[Callable[..., T]] = None,
        **kwargs
    ) -> T:
        # Проверяем, можно ли ходить к сервису
        if not self._can_try_call():
            logger.debug("CircuitBreaker[%s] short-circuit", self.name)
            if fallback:
                return fallback(*args, **kwargs)
            raise ServiceUnavailable(f"Service {self.name} is unavailable (open circuit).")

        if self.state == self.STATE_HALF_OPEN:
            logger.info("CircuitBreaker[%s] HALF_OPEN trial call", self.name)

        try:
            result = func(*args, **kwargs)
        except Exception:
            logger.exception("CircuitBreaker[%s] call failed", self.name)
            self._record_failure()

            if fallback:
                return fallback(*args, **kwargs)
            raise
        else:
            self._record_success()
            return result
