import uuid
from django.db import models


class Car(models.Model):
    class CarType(models.TextChoices):
        SEDAN = "SEDAN", "Sedan"
        SUV = "SUV", "SUV"
        MINIVAN = "MINIVAN", "Minivan"
        ROADSTER = "ROADSTER", "Roadster"

    car_uid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    brand = models.CharField(max_length=80)
    model = models.CharField(max_length=80)
    registration_number = models.CharField(max_length=20)
    power = models.IntegerField(null=True, blank=True)
    price = models.IntegerField()
    type = models.CharField(max_length=20, choices=CarType.choices)
    availability = models.BooleanField(default=True)

    class Meta:
        db_table = "cars"
        indexes = [
            models.Index(fields=["availability"]),
            models.Index(fields=["brand", "model"]),
        ]

    def __str__(self):
        return f"{self.brand} {self.model} ({self.registration_number})"
