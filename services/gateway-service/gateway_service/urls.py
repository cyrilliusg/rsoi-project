"""URL configuration for gateway_service project."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, re_path

from .gateway.views import (
    CarDetailView,
    CarsView,
    RentalDetailView,
    RentalFinishView,
    RentalListView,
    StatisticsProxyView,
)


def health_check(request):
    return JsonResponse({"status": "ok"}, status=200)


urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/v1/cars", CarsView.as_view()),
    path("api/v1/cars/<uuid:carUid>", CarDetailView.as_view()),
    path("api/v1/rental", RentalListView.as_view()),
    path("api/v1/rental/<uuid:rentalUid>", RentalDetailView.as_view()),
    path("api/v1/rental/<uuid:rentalUid>/finish", RentalFinishView.as_view()),
    # Reverse-proxy to statistics-service. Any path under
    # /api/v1/statistics/ is forwarded verbatim (the subpath is whatever
    # comes after /api/v1/statistics/).
    re_path(r"^api/v1/statistics/(?P<subpath>.*)$", StatisticsProxyView.as_view()),
    path('manage/health', health_check, name='health-check'),
]
