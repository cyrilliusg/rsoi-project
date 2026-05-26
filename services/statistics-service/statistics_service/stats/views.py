"""
Admin-only statistics API.

Endpoints (all require role=ADMIN, validated via authlib + IDP JWKs):
  GET /api/v1/statistics/summary
  GET /api/v1/statistics/events?eventType=&from=&to=&page=&size=
  GET /api/v1/statistics/users/{userId}
"""
from __future__ import annotations

from django.db.models import Count
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, views
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from authlib.permissions import IsAdmin

from .models import EventLog
from .serializers import EventLogSerializer

ADMIN_PERMS = [permissions.IsAuthenticated, IsAdmin]


class _Pagination(PageNumberPagination):
    page_query_param = "page"
    page_size_query_param = "size"
    page_size = 20
    max_page_size = 200


class SummaryView(views.APIView):
    permission_classes = ADMIN_PERMS

    def get(self, request):
        qs = EventLog.objects.all()
        by_type = dict(
            qs.values_list("event_type").annotate(c=Count("id")).values_list("event_type", "c")
        )
        rentals_created = qs.filter(event_type="rental.created")
        finished = qs.filter(event_type="rental.finished").count()
        canceled = qs.filter(event_type="rental.canceled").count()
        failed = qs.filter(event_type="rental.failed").count()
        revenue = sum(
            (e.payload or {}).get("totalPrice", 0) or 0 for e in rentals_created
        )
        unique_users = qs.values("user_id").distinct().count()
        return Response({
            "totals": {
                "events": qs.count(),
                "rentalsCreated": rentals_created.count(),
                "rentalsFinished": finished,
                "rentalsCanceled": canceled,
                "rentalsFailed": failed,
                "revenue": revenue,
                "uniqueUsers": unique_users,
            },
            "byEventType": by_type,
        })


class EventsView(views.APIView):
    permission_classes = ADMIN_PERMS

    def get(self, request):
        qs = EventLog.objects.all()
        event_type = request.query_params.get("eventType")
        if event_type:
            qs = qs.filter(event_type=event_type)
        date_from = request.query_params.get("from")
        if date_from:
            dt = parse_datetime(date_from)
            if dt:
                qs = qs.filter(timestamp__gte=dt)
        date_to = request.query_params.get("to")
        if date_to:
            dt = parse_datetime(date_to)
            if dt:
                qs = qs.filter(timestamp__lte=dt)

        paginator = _Pagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            EventLogSerializer(page, many=True).data
        )


class UserStatsView(views.APIView):
    permission_classes = ADMIN_PERMS

    def get(self, request, userId):
        qs = EventLog.objects.filter(user_id=userId)
        by_type = dict(
            qs.values_list("event_type").annotate(c=Count("id")).values_list("event_type", "c")
        )
        spent = sum(
            (e.payload or {}).get("totalPrice", 0) or 0
            for e in qs.filter(event_type="rental.created")
        )
        last = qs.order_by("-timestamp").first()
        return Response({
            "userId": str(userId),
            "username": last.username if last else "",
            "totals": {
                "events": qs.count(),
                "rentalsCreated": qs.filter(event_type="rental.created").count(),
                "rentalsFinished": qs.filter(event_type="rental.finished").count(),
                "rentalsCanceled": qs.filter(event_type="rental.canceled").count(),
                "spent": spent,
            },
            "byEventType": by_type,
            "lastEventAt": last.timestamp if last else None,
        })
