"""
URL configuration for statistics_service project.

Phase 4 will add /api/v1/statistics/* endpoints (admin-only).
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path


def health_check(request):
    return JsonResponse({"status": "ok"}, status=200)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('manage/health', health_check, name='health-check'),
]
