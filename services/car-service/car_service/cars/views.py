from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Car
from .serializers import CarResponseSerializer
from .pagination import ApiPagination

def define_bool(raw_string) -> bool:
    if not isinstance(raw_string, str):
        return True

    if raw_string.lower() in ("false", "0", "no"):
        return False

    return True

class CarViewSet(viewsets.ModelViewSet):
    """
    CRUD для Car.
    GET /api/v1/cars?showAll=true&page=...&size=...
      - по умолчанию только доступные (available=true)
      - c showAll=true вернёт и в резерве (available=false)
    """
    serializer_class = CarResponseSerializer
    pagination_class = ApiPagination
    queryset = Car.objects.all().order_by("id")

    #  UUID в путь-параметрах
    lookup_field = "car_uid"

    def get_queryset(self):
        qs = super().get_queryset()

        show_all_raw = self.request.query_params.get("showAll")
        show_all = define_bool(show_all_raw)

        if not show_all:
            qs = qs.filter(availability=True)
        return qs

    @action(detail=True, methods=["post"], url_path="reserve")
    def reserve(self, request, car_uid=None):
        """Пометить авто как зарезервированное (available=false)."""
        car = self.get_object()
        if car.availability is False:
            return Response({"message": "Авто уже в резерве."}, status=status.HTTP_409_CONFLICT)
        car.availability = False
        car.save(update_fields=["availability"])
        return Response(self.get_serializer(car).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="release")
    def release(self, request, car_uid=None):
        """Снять резерв с авто (available=true)."""
        car = self.get_object()
        if car.availability is True:
            return Response({"message": "Авто уже доступно."}, status=status.HTTP_409_CONFLICT)
        car.availability = True
        car.save(update_fields=["availability"])
        return Response(self.get_serializer(car).data, status=status.HTTP_200_OK)
