from rest_framework import status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Payment
from .serializers import PaymentSerializer, CreatePaymentRequestSerializer


class PaymentViewSet(mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):
    """
    POST   /api/v1/payment               -> создать оплату (status=PAID)
    GET    /api/v1/payment/{paymentUid}  -> получить оплату
    DELETE /api/v1/payment/{paymentUid}  -> пометить оплату CANCELED (идемпотентно)
    POST   /api/v1/payment/{paymentUid}/cancel -> отменить оплату, 409 если уже отменена
    """
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all().order_by("id")
    lookup_field = "payment_uid"
    lookup_value_regex = r"[0-9a-fA-F-]{36}"

    def create(self, request, *args, **kwargs):
        req = CreatePaymentRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        payment = Payment.objects.create(price=req.validated_data["price"], status=Payment.Status.PAID)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        payment = self.get_object()
        return Response(PaymentSerializer(payment).data)

    def destroy(self, request, *args, **kwargs):
        payment = self.get_object()
        if payment.status != Payment.Status.CANCELED:
            payment.status = Payment.Status.CANCELED
            payment.save(update_fields=["status"])
        return Response(status=status.HTTP_204_NO_CONTENT)
