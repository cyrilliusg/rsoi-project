from datetime import date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from . import clients
from .circuit_breaker import ServiceUnavailable
from .task_queue import enqueue_task


def _bearer(request) -> str:
    """Inbound Authorization header (we propagate it to every upstream)."""
    return request.headers.get("Authorization", "")


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

        car_uid = request.data["carUid"]
        date_from = request.data["dateFrom"]
        date_to = request.data["dateTo"]

        # 1. Проверяем авто (критично, без фолбэка)
        try:
            car = clients.get_car(car_uid, token=token)
        except Exception:
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
            return Response(
                {"message": "Failed to create rental"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
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

        # 3. Cancel rental — если не получилось, ставим в очередь
        try:
            clients.cancel_rental(str(rentalUid), token=token)
        except Exception:
            enqueue_task("cancel_rental", {
                "rentalUid": str(rentalUid),
                "token": token,
            })

        # 4. Cancel payment — аналогично
        try:
            clients.cancel_payment(r["paymentUid"], token=token)
        except Exception:
            enqueue_task("cancel_payment", {
                "paymentUid": r["paymentUid"],
                "token": token,
            })

        return Response(status=status.HTTP_204_NO_CONTENT)


class RentalFinishView(APIView):
    """POST /api/v1/rental/{rentalUid}/finish"""

    def post(self, request, rentalUid):
        token = _bearer(request)
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

        return Response(status=status.HTTP_204_NO_CONTENT)
