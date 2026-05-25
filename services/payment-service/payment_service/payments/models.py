import uuid
from django.db import models



class Payment(models.Model):
    class Status(models.TextChoices):
        PAID = "PAID", "Paid"
        CANCELED = "CANCELED", "Canceled"

    id = models.AutoField(primary_key=True)
    payment_uid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PAID)
    price = models.IntegerField()

    class Meta:
        db_table = "payment"
        indexes = [
            models.Index(fields=["payment_uid"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.payment_uid} [{self.status}] {self.price}"