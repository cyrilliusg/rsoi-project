from rest_framework import serializers
from .models import Car

class CarResponseSerializer(serializers.ModelSerializer):
    carUid = serializers.UUIDField(source="car_uid", read_only=True)
    registrationNumber = serializers.CharField(source="registration_number", max_length=20)
    available = serializers.BooleanField(source="availability", required=False)
    power = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Car
        fields = [
            "carUid",
            "brand",
            "model",
            "registrationNumber",
            "power",
            "type",
            "price",
            "available",
        ]