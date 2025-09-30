
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class User(AbstractUser):
    ROLE_CHOICES = (
        ('regular', 'Regular'),
        ('driver', 'Driver'),
        ('admin',  'Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='regular')
    phone_number = models.CharField(max_length=15, blank=True, null=True)

class PickupRequest(models.Model):
    REGULAR = "regular"
    BULKY = "bulky"
    WASTE_TYPES = [(REGULAR, "Regular Waste"), (BULKY, "Bulky Waste")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    waste_type = models.CharField(max_length=10, choices=WASTE_TYPES, default=REGULAR)
    date = models.DateField()
    time = models.TimeField()
    address = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    photo = models.ImageField(upload_to="pickup_photos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):  # handy for admin
        return f"{self.user} — {self.get_waste_type_display()} @ {self.date} {self.time}"

class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} — {self.subject or 'No subject'}"