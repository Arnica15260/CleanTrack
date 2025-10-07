from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models import Q, F, TextChoices
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver



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


    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recycling_logs",
    )
    material = models.CharField(max_length=20)
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


# -------------------- Complaints (general) --------------------

class Complaint(TimeStamped):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="complaints",              # <-- unique, no clash
    )
    complaint_type = models.CharField(max_length=30)
    subject = models.CharField(max_length=120)
    description = models.TextField()
    photo = models.ImageField(upload_to="complaint_photos/", blank=True, null=True)
    status = models.CharField(max_length=20, default="open")  # open|in_progress|resolved

    # Optional links used by the driver/dispatch features:
    task = models.ForeignKey(
        "users.DeliveryTask",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="complaints",
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="driver_complaints_general_link",  # distinct from DriverComplaint.driver
    )

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return f"{self.user} complaint {self.complaint_type} - {self.subject}"


# -------------------- Rewards --------------------

class RewardEvent(TimeStamped):
    """Log of points earned; sum for a user = current points."""
    SOURCES = (

        ("recycling",  "Recycling"),
        ("reuse",      "Reuse"),

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


# -------------------- Driver tasking & tracking --------------------

class DeliveryTask(TimeStamped):
    class Status(TextChoices):
        ASSIGNED  = "assigned",  "Assigned"
        ACCEPTED  = "accepted",  "Accepted"
        ENROUTE   = "enroute",   "En Route"
        ARRIVED   = "arrived",   "Arrived"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    # Who is this delivery for (the customer)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delivery_tasks",
    )

    # Optional link to an existing pickup
    pickup_request = models.ForeignKey(
        "users.PickupRequest",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="tasks",
    )

    # Assignment (driver)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_delivery_tasks",   # <-- changed to avoid clash
        help_text="Driver user",
    )

    address = models.CharField(max_length=255)
    window_start = models.DateTimeField(null=True, blank=True)
    window_end   = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, default="")

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ASSIGNED, db_index=True)

    accepted_at  = models.DateTimeField(null=True, blank=True)
    started_at   = models.DateTimeField(null=True, blank=True)   # enroute
    arrived_at   = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    proof_photo = models.ImageField(upload_to="driver_proof/", null=True, blank=True)

    points_awarded = models.IntegerField(default=0)

    class Meta:
        ordering = ("-created",)
        indexes = [models.Index(fields=("status", "-created"))]

    def __str__(self):
        who = getattr(self.assigned_to, "username", "driver")
        return f"Task to {self.address} for {self.customer} → {who} [{self.status}]"

    # simple helpers used by views
    def award_points(self, driver, pts: int, reason="delivery"):
        DriverPointEvent.objects.create(driver=driver, task=self, points=pts, reason=reason)
        self.points_awarded = (self.points_awarded or 0) + pts
        self.save(update_fields=["points_awarded"])


class DriverLocation(models.Model):
    """Last known live location per driver (for fast queries)."""
    driver = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="driver_location"
    )
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.driver} @ {self.lat},{self.lng} ({self.last_seen})"


class LocationPing(TimeStamped):
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="location_pings")
    task   = models.ForeignKey(DeliveryTask, on_delete=models.SET_NULL, null=True, blank=True, related_name="pings")
    lat    = models.DecimalField(max_digits=9, decimal_places=6)
    lng    = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        ordering = ("-created",)


class DriverPointEvent(TimeStamped):
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="driver_points")
    task   = models.ForeignKey(DeliveryTask, on_delete=models.SET_NULL, null=True, blank=True, related_name="point_events")
    points = models.IntegerField(default=0)
    reason = models.CharField(max_length=80, default="delivery")

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return f"{self.driver} {'+' if self.points >= 0 else ''}{self.points} ({self.reason})"


@receiver(post_save, sender=Complaint)
def penalize_driver_on_complaint(sender, instance: Complaint, created, **kwargs):
    if not created:
        return
    if instance.driver_id:
        DriverPointEvent.objects.create(driver=instance.driver, task=instance.task, points=-5, reason="complaint")

class DriverActivity(models.Model):
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="driver_activities")
    kind = models.CharField(max_length=40, default="event")
    title = models.CharField(max_length=160)
    when = models.DateTimeField(auto_now_add=True)
    row = models.CharField(max_length=16, default="info")  # css color key

    class Meta:
        ordering = ["-when"]


class DriverComplaint(models.Model):
    driver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="driver_complaint")  # unique name
    against_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="complained_by_driver")
    category = models.CharField(max_length=80, default="Service")
    description = models.TextField()
    address = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, default="open")
    when_dt = models.DateTimeField(auto_now_add=True)
    photo = models.ImageField(upload_to="driver_complaint/", blank=True)

    class Meta:
        ordering = ["-when_dt"]

