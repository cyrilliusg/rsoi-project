from django.urls import path

from . import views

urlpatterns = [
    path("api/v1/statistics/summary", views.SummaryView.as_view(), name="stats-summary"),
    path("api/v1/statistics/events", views.EventsView.as_view(), name="stats-events"),
    path("api/v1/statistics/users/<uuid:userId>", views.UserStatsView.as_view(), name="stats-user"),
]
