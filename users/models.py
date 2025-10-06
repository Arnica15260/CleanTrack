from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models import Q, F
from django.utils import timezone


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

    class Status(models.TextChoices):
        PENDING   = "pending", "Pending"
        ACCEPTED  = "accepted", "Accepted"
        DONATED   = "donated", "Donated"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reuse_donations",
    )

    category = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=1)
    partner  = models.CharField(max_length=120, blank=True, default="")
    note     = models.CharField(max_length=255, blank=True, default="")
    photo    = models.ImageField(upload_to="reuse_photos/", blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        related_name="reuses_taken",
        on_delete=models.SET_NULL,
        help_text="User who accepted the item (if any).",
    )
    accepted_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the item was accepted (if accepted).",
    )

    class Meta:
        ordering = ("-created",)
        indexes = [
            models.Index(fields=("status", "created")),
            models.Index(fields=("status", "accepted_at")),
        ]
        constraints = [
            models.CheckConstraint(
                name="reuse_accepted_by_not_self",
                check=Q(accepted_by__isnull=True) | ~Q(accepted_by=F("user")),
            ),
            models.CheckConstraint(
                name="reuse_accept_fields_null_when_pending",
                check=~Q(status="pending") | (Q(accepted_by__isnull=True) & Q(accepted_at__isnull=True)),
            ),

            models.CheckConstraint(
                name="reuse_accept_fields_set_when_accepted",
                check=~Q(status="accepted") | (Q(accepted_by__isnull=False) & Q(accepted_at__isnull=False)),
            ),
        ]

    def __str__(self):
        base = f"{self.user} donated {self.quantity} x {self.category}"
        return f"{base} [{self.status}]" if self.status != self.Status.PENDING else base

    @property
    def item_name(self):
        return self.category

    @property
    def description(self):
        return self.note

    @property
    def is_available(self):
        return self.status == self.Status.PENDING

    # ------- domain helpers -------
    def accept_if_pending(self, user):

        from django.db import transaction
        now = timezone.now()
        with transaction.atomic():
            updated = type(self).objects.filter(
                pk=self.pk,
                status=self.Status.PENDING,
                accepted_by__isnull=True,
                accepted_at__isnull=True,
            ).update(
                status=self.Status.ACCEPTED,
                accepted_by=user,
                accepted_at=now,
            )
            if updated:
                self.refresh_from_db()
                return True
            return False

    def mark_donated(self):
        self.status = self.Status.DONATED
        self.save(update_fields=["status"])

    def cancel(self):
        self.status = self.Status.CANCELLED
        self.accepted_by = None
        self.accepted_at = None
        self.save(update_fields=["status", "accepted_by", "accepted_at"])

    def release(self):
        self.status = self.Status.PENDING
        self.accepted_by = None
        self.accepted_at = None
        self.save(update_fields=["status", "accepted_by", "accepted_at"])


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




