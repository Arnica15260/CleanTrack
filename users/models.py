
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('regular', 'Regular'),
        ('driver', 'Driver'),
        ('admin',  'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='regular')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
