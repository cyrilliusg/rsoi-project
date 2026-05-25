from rest_framework import serializers
from .models import Payment


class CreatePaymentRequestSerializer(serializers.Serializer):
    price = serializers.IntegerField(min_value=0)


class PaymentSerializer(serializers.ModelSerializer):
    paymentUid = serializers.UUIDField(source="payment_uid", read_only=True)
    status = serializers.ChoiceField(choices=Payment.Status.choices, read_only=True)
    price = serializers.IntegerField()

    class Meta:
        model = Payment
        fields = ["paymentUid", "status", "price"]
