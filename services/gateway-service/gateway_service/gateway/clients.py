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

        logger.info("HTTP %s %s params=%s json=%s", method, url, params, json)

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


def _bearer(token: Optional[str]) -> dict[str, str]:
    """
    Build Authorization headers from the inbound bearer token.

    Phase 2: we propagate the caller's JWT to every upstream request so
    every service can independently validate it via the same JWKs.
    """
    if not token:
        return {}
    return {"Authorization": token}


# ==== CAR SERVICE ====
def get_cars(show_all: bool = False, page: int = 0, size: int = 10, *, token: Optional[str] = None):
    params = {"showAll": show_all, "page": page, "size": size}
    headers = _bearer(token)

    def _call():
        r = car_client.get("/cars", params=params, headers=headers)
        return r.json()

    return car_cb.call(_call)


def get_car(car_uid: str, *, token: Optional[str] = None, allow_fallback: bool = False):
    headers = _bearer(token)

    def _call():
        r = car_client.get(f"/cars/{car_uid}", headers=headers)
        return r.json()

    def _fallback():
        if allow_fallback:
            return {"carUid": car_uid}
        raise ServiceUnavailable("Car service unavailable")

    return car_cb.call(_call, fallback=_fallback if allow_fallback else None)


def reserve_car(car_uid: str, *, token: Optional[str] = None) -> None:
    car_client.post(f"/cars/{car_uid}/reserve/", headers=_bearer(token))


def release_car(car_uid: str, *, token: Optional[str] = None) -> None:
    car_client.post(f"/cars/{car_uid}/release/", headers=_bearer(token))


# ==== PAYMENT SERVICE ====
def create_payment(price: float, *, token: Optional[str] = None):
    r = payment_client.post("/payment/", json={"price": price}, headers=_bearer(token))
    return r.json()


def cancel_payment(paymentUid: str, *, token: Optional[str] = None) -> None:
    payment_client.delete(f"/payment/{paymentUid}/", headers=_bearer(token))


def get_payment(payment_uid: str, *, token: Optional[str] = None, allow_fallback: bool = False):
    headers = _bearer(token)

    def _call():
        r = payment_client.get(f"/payment/{payment_uid}", headers=headers)
        return r.json()

    def _fallback():
        if allow_fallback:
            return {"paymentUid": payment_uid}
        raise ServiceUnavailable("Payment service unavailable")

    return payment_cb.call(_call, fallback=_fallback if allow_fallback else None)


# ==== RENTAL SERVICE ====
def create_rental(car_uid: str, payment_uid: str, date_from: str, date_to: str, *, token: Optional[str] = None):
    data = {
        "carUid": car_uid,
        "paymentUid": payment_uid,
        "dateFrom": date_from,
        "dateTo": date_to,
    }
    r = rental_client.post("/rental/", json=data, headers=_bearer(token))
    return r.json()


def get_rentals(*, token: Optional[str] = None):
    headers = _bearer(token)

    def _call():
        r = rental_client.get("/rental", headers=headers)
        return r.json()

    return rental_cb.call(_call)


def get_rental(rental_uid: str, *, token: Optional[str] = None):
    headers = _bearer(token)

    def _call():
        r = rental_client.get(f"/rental/{rental_uid}", headers=headers)
        return r.json()

    return rental_cb.call(_call)


def finish_rental(rental_uid: str, *, token: Optional[str] = None) -> None:
    rental_client.post(f"/rental/{rental_uid}/finish/", headers=_bearer(token))


def cancel_rental(rentalUid: str, *, token: Optional[str] = None) -> None:
    rental_client.delete(f"/rental/{rentalUid}/", headers=_bearer(token))
