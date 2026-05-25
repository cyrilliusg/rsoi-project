import logging
from typing import Any, Optional

import requests
from django.conf import settings

from .circuit_breaker import CircuitBreaker, ServiceUnavailable

logger = logging.getLogger(__name__)


class ServiceClient:
    """Базовый HTTP-клиент для внешних сервисов."""

    def __init__(self, base_url: str, timeout: int = 5):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _request(self,
                 method: str, path: str, *, params: Optional[dict[str, Any]] = None,
                 json: Optional[dict[str, Any]] = None, headers: Optional[dict[str, str]] = None,
                 **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"

        kwargs.setdefault("timeout", self.timeout)

        logger.info("HTTP %s %s params=%s json=%s headers=%s", method, url, params, json, headers)

        try:
            response = self.session.request(method, url, params=params, json=json, headers=headers, **kwargs)
        except requests.RequestException:
            logger.exception("HTTP %s %s failed", method, url)
            raise

        try:
            text = response.text
            content_preview = text[:1000] + ("..." if len(text) > 1000 else "")
        except Exception:
            content_preview = "<non-text response>"

        logger.info("HTTP %s %s -> %s response=%s", method, url, response.status_code, content_preview)
        response.raise_for_status()
        return response

    def get(self, path: str, **kwargs) -> requests.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self._request("POST", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self._request("DELETE", path, **kwargs)


# Клиенты для сервисов
car_client = ServiceClient(settings.CAR_SERVICE_URL)
payment_client = ServiceClient(settings.PAYMENT_SERVICE_URL)
rental_client = ServiceClient(settings.RENTAL_SERVICE_URL)

# Circuit breakers
car_cb = CircuitBreaker("car_service", failure_threshold=3, recovery_timeout=10)
payment_cb = CircuitBreaker("payment_service", failure_threshold=3, recovery_timeout=10)
rental_cb = CircuitBreaker("rental_service", failure_threshold=3, recovery_timeout=10)


def _user_headers(username: str) -> dict[str, str]:
    return {"X-User-Name": username}


# ==== CAR SERVICE (READ, with CB) ====
def get_cars(show_all: bool = False, page: int = 0, size: int = 10):
    params = {"showAll": show_all, "page": page, "size": size}

    def _call():
        r = car_client.get("/cars", params=params)
        return r.json()

    # Car Service для /cars – критичен, поэтому фолбэка нет → ошибка поднимется вверх
    return car_cb.call(_call)


def get_car(car_uid: str, allow_fallback: bool = False):
    def _call():
        r = car_client.get(f"/cars/{car_uid}")
        return r.json()

    def _fallback():
        if allow_fallback:
            # Фолбэк: только uid
            return {"carUid": car_uid}
        # Критичный сценарий (например, POST /rental)
        raise ServiceUnavailable("Car service unavailable")

    return car_cb.call(_call, fallback=_fallback if allow_fallback else None)


def reserve_car(car_uid: str) -> None:
    # запись состояния – без circuit breaker
    car_client.post(f"/cars/{car_uid}/reserve/")


def release_car(car_uid: str) -> None:
    car_client.post(f"/cars/{car_uid}/release/")


# ==== PAYMENT SERVICE (READ, with CB) ====
def create_payment(price: float):
    r = payment_client.post("/payment/", json={"price": price})
    return r.json()


def cancel_payment(paymentUid: str) -> None:
    payment_client.delete(f"/payment/{paymentUid}/")


def get_payment(payment_uid: str, allow_fallback: bool = False):
    def _call():
        r = payment_client.get(f"/payment/{payment_uid}")
        return r.json()

    def _fallback():
        if allow_fallback:
            return {"paymentUid": payment_uid}
        raise ServiceUnavailable("Payment service unavailable")

    return payment_cb.call(_call, fallback=_fallback if allow_fallback else None)


# ==== RENTAL SERVICE (READ, with CB) ====
def create_rental(username: str, car_uid: str, payment_uid: str, date_from: str, date_to: str):
    data = {
        "carUid": car_uid,
        "paymentUid": payment_uid,
        "dateFrom": date_from,
        "dateTo": date_to}
    headers = _user_headers(username)
    r = rental_client.post("/rental/", json=data, headers=headers)
    return r.json()


def get_rentals(username: str):
    headers = _user_headers(username)

    def _call():
        r = rental_client.get("/rental", headers=headers)
        return r.json()

    # Rental Service для списка аренды – критичен → фолбэка нет
    return rental_cb.call(_call)


def get_rental(username: str, rental_uid: str):
    headers = _user_headers(username)

    def _call():
        r = rental_client.get(f"/rental/{rental_uid}", headers=headers)
        return r.json()

    return rental_cb.call(_call)


def finish_rental(username: str, rental_uid: str) -> None:
    headers = _user_headers(username)
    rental_client.post(f"/rental/{rental_uid}/finish/", headers=headers)


def cancel_rental(username: str, rentalUid: str) -> None:
    headers = _user_headers(username)
    rental_client.delete(f"/rental/{rentalUid}/", headers=headers)
