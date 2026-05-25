import zoneinfo
from datetime import datetime

from django.utils.timezone import make_aware
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Rental
from .serializers import CreateRentalRequestSerializer, RentalShortSerializer
from .permissions import HasUserHeader


def _username(request) -> str:
    return request.headers.get("X-User-Name")


def _to_aware_midnight(d):
    # d: date -> aware datetime UTC 00:00
    return make_aware(datetime(d.year, d.month, d.day, 0, 0, 0), timezone=zoneinfo.ZoneInfo('UTC'))


class RentalViewSet(viewsets.ViewSet):
    """
    /api/v1/rental:
      GET  -> список аренд пользователя (по X-User-Name)
      POST -> создать аренду (IN_PROGRESS)

    /api/v1/rental/{rentalUid}:
      GET    -> аренда пользователя (проверка владения)
      DELETE -> отмена аренды (CANCELED)

    /api/v1/rental/{rentalUid}/finish:
      POST -> завершить аренду (FINISHED)
    """
    permission_classes = [HasUserHeader]

    def list(self, request):
        user = _username(request)
        rentals = Rental.objects.filter(username=user).order_by("-id")
        return Response(RentalShortSerializer(rentals, many=True).data)

    def retrieve(self, request, pk=None):
        user = _username(request)
        rental = get_object_or_404(Rental, rental_uid=pk)
        if rental.username != user:
            return Response({"message": "Аренда не найдена"}, status=status.HTTP_404_NOT_FOUND)
        return Response(RentalShortSerializer(rental).data)

    def create(self, request):
        user = _username(request)
        ser = CreateRentalRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        car_uid = ser.validated_data["carUid"]
        payment_uid = ser.validated_data["paymentUid"]
        date_from = _to_aware_midnight(ser.validated_data["dateFrom"])
        date_to = _to_aware_midnight(ser.validated_data["dateTo"])

        rental = Rental.objects.create(
            username=user,
            car_uid=car_uid,
            payment_uid=payment_uid,
            date_from=date_from,
            date_to=date_to,
            status=Rental.Status.IN_PROGRESS,
        )
        return Response(RentalShortSerializer(rental).data, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        user = _username(request)
        rental = get_object_or_404(Rental, rental_uid=pk)
        if rental.username != user:
            return Response({"message": "Аренда не найдена"}, status=status.HTTP_404_NOT_FOUND)
        if rental.status == Rental.Status.CANCELED:
            return Response(status=status.HTTP_204_NO_CONTENT)
        rental.status = Rental.Status.CANCELED
        rental.save(update_fields=["status"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="finish")
    def finish(self, request, pk=None):
        user = _username(request)
        rental = get_object_or_404(Rental, rental_uid=pk)
        if rental.username != user:
            return Response({"message": "Аренда не найдена"}, status=status.HTTP_404_NOT_FOUND)
        if rental.status == Rental.Status.FINISHED:
            return Response(status=status.HTTP_204_NO_CONTENT)
        rental.status = Rental.Status.FINISHED
        rental.save(update_fields=["status"])
        return Response(status=status.HTTP_204_NO_CONTENT)
