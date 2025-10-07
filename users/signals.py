
from .models import PickupRequest, RecyclingLog, ReuseDonation, Complaint, RewardEvent
import math
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
User = get_user_model()

@receiver(post_save, sender=PickupRequest)
def reward_pickup(sender, instance, created, **kwargs):
    if created:
        RewardEvent.objects.create(user=instance.user, source="pickup", points=5, memo="Scheduled pickup")

@receiver(post_save, sender=RecyclingLog)
def reward_recycle(sender, instance, created, **kwargs):
    if created:
        pts = max(2, int(round(float(instance.weight_kg) * 2)))
        RewardEvent.objects.create(user=instance.user, source="recycling", points=pts, memo=f"Recycled {instance.material}")

@receiver(post_save, sender=ReuseDonation)
def reward_reuse(sender, instance, created, **kwargs):
    if created:
        pts = min(25, 5 * int(instance.quantity))
        RewardEvent.objects.create(user=instance.user, source="reuse", points=pts, memo=f"Donated {instance.category}")

@receiver(post_save, sender=Complaint)
def reward_complaint(sender, instance, created, **kwargs):
    # Only award when status becomes resolved (not at creation)
    if not created and instance.status == "resolved":
        RewardEvent.objects.create(user=instance.user, source="complaint", points=10, memo="Complaint resolved")

@receiver(post_save, sender=User)
def ensure_driver_profile(sender, instance, created, **kwargs):
    return
