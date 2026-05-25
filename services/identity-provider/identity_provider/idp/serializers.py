"""Serializers for IdP endpoints."""
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    sub = serializers.UUIDField(read_only=True)

    class Meta:
        model = User
        fields = ["sub", "username", "email", "first_name", "last_name", "role"]
        read_only_fields = ["sub"]


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=4)

    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name", "last_name", "role"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
