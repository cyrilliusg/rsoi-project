"""URL configuration for identity_provider project."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    return JsonResponse({"status": "ok"}, status=200)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('manage/health', health_check, name='health-check'),
    path('', include('identity_provider.idp.urls')),
]
