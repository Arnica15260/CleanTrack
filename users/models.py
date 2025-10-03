from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


# -------------------- Custom User --------------------

class User(AbstractUser):
    ROLE_CHOICES = (
        ("regular", "Regular"),
        ("driver",  "Driver"),
        ("admin",   "Admin"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="regular")
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.username


# -------------------- Common --------------------

class TimeStamped(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# -------------------- Pickup --------------------

class PickupRequest(models.Model):
    WASTE_TYPES = [
        ("regular", "Regular Waste"),
        ("bulky",   "Bulky Waste"),
    ]
    STATUS = [
        ("pending",   "Pending"),
        ("scheduled", "Scheduled"),
        ("enroute",   "En Route"),
        ("done",      "Completed"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pickup_requests",
    )
    waste_type = models.CharField(max_length=16, choices=WASTE_TYPES, default="regular")
    date = models.DateField()
    time = models.TimeField()
    address = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    photo = models.ImageField(upload_to="pickup_photos/", blank=True, null=True)
    status = models.CharField(max_length=16, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-time"]

    def __str__(self):
        return f"{self.user} • {self.waste_type} • {self.date} {self.time}"


# -------------------- Contact --------------------

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


# -------------------- Recycling --------------------

class RecyclingLog(TimeStamped):
    MATERIALS = (
        ("paper",   "Paper/Cardboard"),
        ("plastic", "Plastics"),
        ("metal",   "Metals"),
        ("glass",   "Glass"),
        ("ewaste",  "E-waste"),
        ("battery", "Batteries"),
        ("other",   "Other"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recycling_logs",
    )
    material = models.CharField(max_length=20, choices=MATERIALS)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2)  # e.g. 12.50 kg
    note = models.CharField(max_length=255, blank=True, default="")
    photo = models.ImageField(upload_to="recycle_photos/", blank=True, null=True)

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return f"{self.user} recycled {self.material} ({self.weight_kg} kg)"


# -------------------- Reuse / Donation --------------------

class ReuseDonation(TimeStamped):
    # Make category FREE TEXT so people can donate anything
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reuse_donations"
    )
    category = models.CharField(max_length=50)  # ← no choices
    quantity = models.PositiveIntegerField(default=1)
    partner = models.CharField(max_length=120, blank=True, default="")
    note = models.CharField(max_length=255, blank=True, default="")
    photo = models.ImageField(upload_to="reuse_photos/", blank=True, null=True)

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return f"{self.user} donated {self.quantity} x {self.category}"


# -------------------- Complaint --------------------

class Complaint(TimeStamped):
    TYPES = (
        ("missed_pickup", "Missed Pickup"),
        ("damage",        "Property Damage"),
        ("billing",       "Billing Issue"),
        ("driver",        "Driver Concern"),
        ("other",         "Other"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="complaints",
    )
    complaint_type = models.CharField(max_length=30, choices=TYPES)
    subject = models.CharField(max_length=120)
    description = models.TextField()
    photo = models.ImageField(upload_to="complaint_photos/", blank=True, null=True)
    status = models.CharField(max_length=20, default="open")  # open|in_progress|resolved

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return f"{self.user} complaint {self.complaint_type} - {self.subject}"


# -------------------- Rewards --------------------

class RewardEvent(TimeStamped):
    """Log of points earned; sum for a user = current points."""
    SOURCES = (
        ("pickup",     "Pickup"),
        ("recycling",  "Recycling"),
        ("reuse",      "Reuse"),
        ("complaint",  "Complaint Resolution"),
        ("bonus",      "Bonus"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reward_events",
    )
    source = models.CharField(max_length=20, choices=SOURCES)
    points = models.IntegerField(default=0)
    memo = models.CharField(max_length=160, blank=True, default="")

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return f"{self.user} +{self.points} ({self.source})"
