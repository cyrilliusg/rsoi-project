import uuid
from django.db import models


class Rental(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        FINISHED = "FINISHED", "Finished"
        CANCELED = "CANCELED", "Canceled"

    id = models.AutoField(primary_key=True)
    rental_uid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    username = models.CharField(max_length=80)
    payment_uid = models.UUIDField()
    car_uid = models.UUIDField()
    date_from = models.DateTimeField()
    date_to = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)

    class Meta:
        db_table = "rental"
        indexes = [
            models.Index(fields=["rental_uid"]),
            models.Index(fields=["username"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.rental_uid} {self.username} [{self.status}]"
