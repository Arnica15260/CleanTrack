from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User
from .models import PickupRequest
from .models import ContactMessage
from .models import PickupRequest, RecyclingLog, ReuseDonation, Complaint, RewardEvent

class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_active")
    search_fields = ("username", "email", "phone_number")
    ordering = ("id",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "phone_number", "role")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "phone_number", "role", "password1", "password2"),
        }),
    )

admin.site.register(User, UserAdmin)
@admin.register(PickupRequest)
class PickupRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "waste_type", "date", "time", "status", "created_at")
    list_filter = ("waste_type", "status", "date")
    search_fields = ("user__username", "user__email", "address", "notes")



@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "created_at", "is_resolved")
    list_filter = ("is_resolved", "created_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("name", "email", "subject", "message", "created_at")






@admin.register(RecyclingLog)
class RecyclingAdmin(admin.ModelAdmin):
    list_display = ("user","material","weight_kg","created")
    list_filter = ("material",)
    search_fields = ("user__username","note")

@admin.register(ReuseDonation)
class ReuseAdmin(admin.ModelAdmin):
    list_display = ("user","category","quantity","partner","created")
    list_filter = ("category",)
    search_fields = ("user__username","partner","note")

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("user","complaint_type","subject","status","created")
    list_filter = ("complaint_type","status")
    search_fields = ("user__username","subject","description")

@admin.register(RewardEvent)
class RewardAdmin(admin.ModelAdmin):
    list_display = ("user","source","points","memo","created")
    list_filter = ("source",)
    search_fields = ("user__username","memo")

# users/admin.py
from django.contrib import admin
from .models import DeliveryTask, DriverLocation, LocationPing, DriverPointEvent

@admin.register(DeliveryTask)
class DeliveryTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "assigned_to", "address", "status", "window_start", "completed_at")
    list_filter  = ("status", "assigned_to")
    search_fields = ("address", "customer__username", "assigned_to__username")
    autocomplete_fields = ("customer", "assigned_to", "pickup_request")

@admin.register(DriverLocation)
class DriverLocationAdmin(admin.ModelAdmin):
    list_display = ("driver", "lat", "lng", "last_seen")
    search_fields = ("driver__username",)

@admin.register(LocationPing)
class LocationPingAdmin(admin.ModelAdmin):
    list_display = ("driver", "task", "lat", "lng", "created")
    list_filter = ("driver", "task")

@admin.register(DriverPointEvent)
class DriverPointEventAdmin(admin.ModelAdmin):
    list_display = ("driver", "task", "points", "reason", "created")
    list_filter  = ("driver", "reason")
