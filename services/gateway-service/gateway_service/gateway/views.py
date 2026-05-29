from datetime import date

import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from . import clients
from .circuit_breaker import ServiceUnavailable
from .kafka_producer import emit_event
from .task_queue import enqueue_task


def _bearer(request) -> str:
    """Inbound Authorization header (we propagate it to every upstream)."""
    return request.headers.get("Authorization", "")


def _principal(request):
    """Return (user_id, username) from the LightUser put on request by authlib."""
    user = getattr(request, "user", None)
    sub = getattr(user, "sub", "") or ""
    username = getattr(user, "username", "") or ""
    return sub, username


def _forward_upstream_error(exc: requests.HTTPError) -> Response:
    """Forward upstream 4xx/5xx response verbatim (status + JSON body).

    Used on admin write operations where validation errors and 403 from
    car-service must reach the client, not be flattened to 503.
    """
    resp = exc.response
    if resp is None:
        return Response(
            {"message": "Upstream error"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    try:
        body = resp.json()
    except ValueError:
        body = {"message": resp.text or "Upstream error"}
    return Response(body, status=resp.status_code)


class CarsView(APIView):
    def get(self, request):
        show_all = request.query_params.get("showAll") == "true"
        page = int(request.query_params.get("page", 1))
        size = int(request.query_params.get("size", 10))
        token = _bearer(request)

        try:
            cars = clients.get_cars(show_all, page, size, token=token)
        except ServiceUnavailable:
            return Response(
                {"message": "Car Service is unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception:
            return Response(
                {"message": "Failed to load cars"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return Response(cars)

    def post(self, request):
        """Создать автомобиль (admin-only — проверка на car-service по JWT)."""
        token = _bearer(request)
        try:
            car = clients.create_car(request.data, token=token)
        except requests.HTTPError as e:
            return _forward_upstream_error(e)
        except requests.RequestException:
            return Response(
                {"message": "Car Service is unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(car, status=status.HTTP_201_CREATED)


class CarDetailView(APIView):
    """GET/PUT/PATCH/DELETE /api/v1/cars/{carUid}"""

    def get(self, request, carUid):
        token = _bearer(request)
        try:
            car = clients.get_car(str(carUid), token=token)
        except requests.HTTPError as e:
            return _forward_upstream_error(e)
        except (ServiceUnavailable, requests.RequestException):
            return Response(
                {"message": "Car Service is unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(car)

    def put(self, request, carUid):
        return self._update(request, carUid, partial=False)

    def patch(self, request, carUid):
        return self._update(request, carUid, partial=True)

    def _update(self, request, carUid, *, partial: bool):
        token = _bearer(request)
        try:
            car = clients.update_car(str(carUid), request.data, partial=partial, token=token)
        except requests.HTTPError as e:
            return _forward_upstream_error(e)
        except requests.RequestException:
            return Response(
                {"message": "Car Service is unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(car)

    def delete(self, request, carUid):
        token = _bearer(request)
        try:
            clients.delete_car(str(carUid), token=token)
        except requests.HTTPError as e:
            return _forward_upstream_error(e)
        except requests.RequestException:
            return Response(
                {"message": "Car Service is unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class RentalListView(APIView):
    def get(self, request):
        token = _bearer(request)

        try:
            rentals = clients.get_rentals(token=token)
        except ServiceUnavailable:
            return Response(
                {"message": "Rental Service is unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception:
            return Response(
                {"message": "Failed to load rentals"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        enriched = []
        for r in rentals:
            car = clients.get_car(r["carUid"], token=token, allow_fallback=True)
            payment = clients.get_payment(r["paymentUid"], token=token, allow_fallback=True)

            car_block = {"carUid": car["carUid"]}
            if "brand" in car:
                car_block.update({
                    "brand": car["brand"],
                    "model": car["model"],
                    "registrationNumber": car["registrationNumber"],
                })

            payment_block = {"paymentUid": payment["paymentUid"]}
            if "status" in payment:
                payment_block.update({
                    "status": payment["status"],
                    "price": payment["price"],
                })

            enriched.append({
                "rentalUid": r["rentalUid"],
                "status": r["status"],
                "dateFrom": r["dateFrom"],
                "dateTo": r["dateTo"],
                "car": car_block,
                "payment": payment_block,
            })
        return Response(enriched)

    def post(self, request):
        token = _bearer(request)
        user_id, username = _principal(request)

        car_uid = request.data["carUid"]
        date_from = request.data["dateFrom"]
        date_to = request.data["dateTo"]

        def _emit_failed(stage: str, reason: str):
            emit_event(
                "rental.failed",
                user_id=user_id, username=username, correlation_id=car_uid,
                data={
                    "carUid": car_uid,
                    "dateFrom": date_from,
                    "dateTo": date_to,
                    "stage": stage,
                    "reason": reason,
                },
            )

        # 1. Проверяем авто (критично, без фолбэка)
        try:
            car = clients.get_car(car_uid, token=token)
        except Exception:
            _emit_failed("get_car", "Car service unavailable or car not found")
            return Response(
                {"message": "Car Service is unavailable or car not found"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        price_per_day = car["price"]

        d1, d2 = date.fromisoformat(date_from), date.fromisoformat(date_to)
        total_days = (d2 - d1).days
        total_price = price_per_day * total_days

        # 2. Резервируем автомобиль
        try:
            clients.reserve_car(car_uid, token=token)
        except Exception:
            _emit_failed("reserve_car", "Reserve failed")
            return Response(
                {"message": "Failed to reserve car"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # 3. Создаём оплату
        try:
            payment = clients.create_payment(total_price, token=token)
            payment_uid = payment['paymentUid']
        except Exception:
            try:
                clients.release_car(car_uid, token=token)
            except Exception:
                pass
            _emit_failed("create_payment", "Payment service unavailable")
            return Response(
                {"message": "Payment Service unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            # 4. Создаём запись аренды
            rental = clients.create_rental(car_uid, payment_uid, date_from, date_to, token=token)
            rental_uid = rental["rentalUid"]
        except Exception:
            try:
                clients.release_car(car_uid, token=token)
            except Exception:
                pass
            try:
                clients.cancel_payment(payment_uid, token=token)
            except Exception:
                pass
            _emit_failed("create_rental", "Rental service unavailable")
            return Response(
                {"message": "Failed to create rental"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        emit_event(
            "rental.created",
            user_id=user_id, username=username, correlation_id=rental_uid,
            data={
                "rentalUid": rental_uid,
                "carUid": car_uid,
                "paymentUid": payment_uid,
                "dateFrom": date_from,
                "dateTo": date_to,
                "totalDays": total_days,
                "totalPrice": total_price,
                "status": rental["status"],
            },
        )

        return Response({
            "rentalUid": rental_uid,
            "status": rental["status"],
            "carUid": car_uid,
            "dateFrom": date_from,
            "dateTo": date_to,
            "payment": payment,
        }, status=status.HTTP_200_OK)


class RentalDetailView(APIView):
    """GET/DELETE /api/v1/rental/{rentalUid}"""

    def get(self, request, rentalUid):
        token = _bearer(request)

        try:
            r = clients.get_rental(str(rentalUid), token=token)
        except ServiceUnavailable:
            return Response(
                {"message": "Rental Service is unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception:
            return Response(
                {"message": "Failed to load rental"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        car = clients.get_car(r["carUid"], token=token, allow_fallback=True)
        payment = clients.get_payment(r["paymentUid"], token=token, allow_fallback=True)

        car_block = {"carUid": car["carUid"]}
        if "brand" in car:
            car_block.update({
                "brand": car["brand"],
                "model": car["model"],
                "registrationNumber": car["registrationNumber"],
            })

        payment_block = {"paymentUid": payment["paymentUid"]}
        if "status" in payment:
            payment_block.update({
                "status": payment["status"],
                "price": payment["price"],
            })

        return Response({
            "rentalUid": r["rentalUid"],
            "status": r["status"],
            "dateFrom": r["dateFrom"],
            "dateTo": r["dateTo"],
            "car": car_block,
            "payment": payment_block,
        })

    def delete(self, request, rentalUid):
        """Отмена аренды: release car + cancel rental + cancel payment (часть — через очередь)"""
        token = _bearer(request)
        user_id, username = _principal(request)

        # 1. Читаем аренду (критично)
        try:
            r = clients.get_rental(str(rentalUid), token=token)
        except Exception:
            return Response(
                {"message": "Failed to load rental"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # 2. Снимаем резерв с автомобиля
        try:
            clients.release_car(r["carUid"], token=token)
        except Exception:
            return Response(
                {"message": "Failed to release car"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        rental_canceled = True
        payment_canceled = True

        # 3. Cancel rental — если не получилось, ставим в очередь
        try:
            clients.cancel_rental(str(rentalUid), token=token)
        except Exception:
            rental_canceled = False
            enqueue_task("cancel_rental", {
                "rentalUid": str(rentalUid),
                "token": token,
            })

        # 4. Cancel payment — аналогично
        try:
            clients.cancel_payment(r["paymentUid"], token=token)
        except Exception:
            payment_canceled = False
            enqueue_task("cancel_payment", {
                "paymentUid": r["paymentUid"],
                "token": token,
            })

        emit_event(
            "rental.canceled",
            user_id=user_id, username=username, correlation_id=str(rentalUid),
            data={
                "rentalUid": str(rentalUid),
                "carUid": r["carUid"],
                "paymentUid": r["paymentUid"],
                "previousStatus": r.get("status"),
                "newStatus": "CANCELED",
                "compensations": {
                    "rentalCanceled": rental_canceled,
                    "paymentCanceled": payment_canceled,
                    "carReleased": True,
                },
            },
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class RentalFinishView(APIView):
    """POST /api/v1/rental/{rentalUid}/finish"""

    def post(self, request, rentalUid):
        token = _bearer(request)
        user_id, username = _principal(request)
        try:
            r = clients.get_rental(str(rentalUid), token=token)
        except Exception:
            return Response(
                {"message": "Failed to load rental"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            clients.release_car(r["carUid"], token=token)
            clients.finish_rental(str(rentalUid), token=token)
        except Exception:
            return Response(
                {"message": "Failed to finish rental"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        emit_event(
            "rental.finished",
            user_id=user_id, username=username, correlation_id=str(rentalUid),
            data={
                "rentalUid": str(rentalUid),
                "carUid": r["carUid"],
                "previousStatus": r.get("status"),
                "newStatus": "FINISHED",
            },
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class StatisticsProxyView(APIView):
    """
    Thin reverse proxy for statistics-service.

    Gateway is the only ingress for clients; admin role is re-checked
    on statistics-service via JWT, but we forward the inbound token
    verbatim so we don't duplicate the role check here.
    """

    def get(self, request, subpath: str):
        base = settings.STATISTICS_SERVICE_URL.rstrip("/")
        url = f"{base}/statistics/{subpath}"
        headers = {}
        auth = request.headers.get("Authorization")
        if auth:
            headers["Authorization"] = auth
        try:
            upstream = requests.get(
                url,
                params=request.query_params,
                headers=headers,
                timeout=10,
            )
        except requests.RequestException:
            return Response(
                {"message": "Statistics Service is unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            data = upstream.json()
        except ValueError:
            data = {"raw": upstream.text}
        return Response(data, status=upstream.status_code)
