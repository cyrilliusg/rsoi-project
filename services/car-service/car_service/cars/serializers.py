from rest_framework import serializers
from .models import Car

class CarResponseSerializer(serializers.ModelSerializer):
    carUid = serializers.UUIDField(source="car_uid", read_only=True)
    registrationNumber = serializers.CharField(source="registration_number")
    available = serializers.BooleanField(source="availability")

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