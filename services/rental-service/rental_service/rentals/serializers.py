from rest_framework import serializers
from .models import Rental


class CreateRentalRequestSerializer(serializers.Serializer):
    carUid = serializers.UUIDField()
    paymentUid = serializers.UUIDField()
    dateFrom = serializers.DateField()  # вход как YYYY-MM-DD
    dateTo = serializers.DateField()

    def validate(self, attrs):
        if attrs["dateTo"] <= attrs["dateFrom"]:
            raise serializers.ValidationError({"dateTo": "dateTo должен быть позже dateFrom"})
        return attrs


class RentalShortSerializer(serializers.ModelSerializer):
    rentalUid = serializers.UUIDField(source="rental_uid", read_only=True)
    carUid = serializers.UUIDField(source="car_uid", read_only=True)
    paymentUid = serializers.UUIDField(source="payment_uid", read_only=True)
    dateFrom = serializers.DateTimeField(source="date_from", read_only=True, format="%Y-%m-%d")
    dateTo = serializers.DateTimeField(source="date_to", read_only=True, format="%Y-%m-%d")

    class Meta:
        model = Rental
        fields = ["rentalUid", "status", "dateFrom", "dateTo", "carUid", "paymentUid"]
