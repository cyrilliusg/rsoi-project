from rest_framework import serializers

from .models import EventLog


class EventLogSerializer(serializers.ModelSerializer):
    eventId = serializers.UUIDField(source="event_id", read_only=True)
    eventType = serializers.CharField(source="event_type", read_only=True)
    userId = serializers.UUIDField(source="user_id", read_only=True)
    correlationId = serializers.CharField(source="correlation_id", read_only=True)

    class Meta:
        model = EventLog
        fields = [
            "eventId",
            "eventType",
            "timestamp",
            "userId",
            "username",
            "correlationId",
            "payload",
        ]
