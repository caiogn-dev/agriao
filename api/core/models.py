from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)  # Garante unicidade do email
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    zip = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.username

