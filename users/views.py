from datetime import date as dt_date, datetime, timedelta, timezone as py_tz
from zoneinfo import ZoneInfo
from django.conf import settings
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.views import LoginView
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.db import models
from django.template.loader import render_to_string
from django.urls import reverse, NoReverseMatch
from django.views.decorators.http import require_POST
from .models import ReuseDonation
from .forms import (
    RegisterForm, LoginEmailOrUsernameForm, PickupRequestForm, ContactForm,
    RecyclingForm, ReuseForm, ComplaintForm,
)
from .tokens import account_activation_token
from .models import (
  PickupRequest,
    Complaint)

import json

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import DriverComplaintForm
from .models import (
    DeliveryTask,
    DriverActivity,
    DriverComplaint,
    DriverLocation,
    LocationPing,
    DriverPointEvent,
)

User = get_user_model()


# -------- timezone helper (Django 5.x friendly) --------
def _to_dhaka(dt):
    if not dt:
        return None
    dhaka = ZoneInfo("Asia/Dhaka")
    if timezone.is_naive(dt):
        if getattr(settings, "USE_TZ", True):
            dt = timezone.make_aware(dt, timezone.get_default_timezone())
        else:
            return dt.replace(tzinfo=dhaka)
    return dt.astimezone(dhaka)


def _status_class(name):
    s = (name or "").lower()
    if s in {"done", "completed", "verified", "donated", "resolved", "accepted"}:
        return "ok"
    if s in {"cancelled", "rejected"}:
        return "bad"
    if s in {"assigned", "logged", "scheduled", "in_progress"}:
        return "info"
    return "warn"  # pending/default


def _safe_order(qs, fields):
    from django.core.exceptions import FieldError
    for f in fields:
        try:
            return qs.order_by(f)
        except FieldError:
            pass
    return qs


def _decorate_collections(pickups, donations, complaints):
    """Attach presentation helpers that templates read (no underscores)."""
    for p in pickups:
        if not hasattr(p, "vehicle"):
            setattr(p, "vehicle", "Van")
        when = None
        if getattr(p, "date", None) and getattr(p, "time", None):
            when = datetime.combine(p.date, p.time)
        elif getattr(p, "created_at", None):
            when = p.created_at
        setattr(p, "when_dt", _to_dhaka(when))
        setattr(p, "row_class", _status_class(getattr(p, "status", None)))

    for d in donations:
        if not hasattr(d, "item_name"):
            setattr(d, "item_name", "")
        if not hasattr(d, "description"):
            setattr(d, "description", getattr(d, "note", "") or "")
        if not hasattr(d, "status"):
            setattr(d, "status", "pending")
        setattr(d, "when_dt", _to_dhaka(getattr(d, "created", None)))
        setattr(d, "row_class", _status_class(getattr(d, "status", None)))

    for c in complaints:
        if not hasattr(c, "category"):
            try:
                display = c.get_complaint_type_display()
            except Exception:
                display = getattr(c, "complaint_type", "") or "General"
            setattr(c, "category", display)
        setattr(c, "when_dt", _to_dhaka(getattr(c, "created", None)))
        setattr(c, "row_class", _status_class(getattr(c, "status", None)))


def _decorate_rewards(events):
    out = []
    for r in events:
        src_code = (getattr(r, "source", "") or "").lower()
        try:
            src_label = r.get_source_display()
        except Exception:
            src_label = src_code.title() or "Activity"

        note = (
            getattr(r, "memo", None)
            or getattr(r, "note", None)
            or getattr(r, "reason", None)
            or getattr(r, "description", None)
            or getattr(r, "title", None)
            or getattr(r, "details", None)
            or ""
        ).strip()

        if src_code == "reuse":
            title = f"Donated {note}".strip() if note else "Donation"
        elif src_code == "recycling":
            title = f"Recycled {note}".strip() if note else "Recycling"
        elif src_code == "pickup":
            title = note or "Pickup bonus"
        elif src_code == "complaint":
            title = note or "Complaint resolved"
        elif src_code == "bonus":
            title = note or "Bonus"
        else:
            title = note or src_label or "Activity"

        setattr(r, "title_text", title)
        setattr(r, "source_text", src_label)
        setattr(r, "note_text", note or "—")
        setattr(r, "created_dhaka", _to_dhaka(getattr(r, "created", None)))
        out.append(r)
    return out


# =========================  Auth  =========================
class RoleLoginView(LoginView):
    template_name = "login.html"
    authentication_form = LoginEmailOrUsernameForm
    redirect_authenticated_user = False

    def get_success_url(self):
        u = self.request.user
        if u.is_superuser or (getattr(u, "role", "") == "admin" and u.is_staff):
            return "/admin/"
        return reverse("users:dashboard")


def signup_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            from django.utils.encoding import force_bytes
            from django.utils.http import urlsafe_base64_encode

            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = account_activation_token.make_token(user)
            path = reverse("users:activate", kwargs={"uidb64": uidb64, "token": token})
            activate_url = (
                f"{settings.SITE_DOMAIN}{path}"
                if getattr(settings, "SITE_DOMAIN", None)
                else request.build_absolute_uri(path)
            )
            ctx = {"user": user, "activate_url": activate_url}
            msg = EmailMultiAlternatives(
                "Activate your CleanTrack account",
                render_to_string("users/activation_email.txt", ctx),
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
            msg.attach_alternative(
                render_to_string("users/activation_email.html", ctx), "text/html"
            )
            msg.send()
            messages.success(
                request,
                "We emailed you an activation link. Please verify to log in.",
            )
            return redirect("users:login")
    else:
        form = RegisterForm()
    return render(request, "register.html", {"form": form})


def activate(request, uidb64, token):
    from django.utils.encoding import force_str
    from django.utils.http import urlsafe_base64_decode

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except Exception:
        user = None
    if user and account_activation_token.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save()
        messages.success(request, "Email verified — you can log in now.")
        return redirect("users:login")
    return render(request, "activation_invalid.html", status=400)


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("users:login")


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def signup_admin(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = "admin"
            user.is_staff = True
            user.is_active = True
            user.save()
            messages.success(request, f"Admin user '{user.username}' created.")
            return redirect("users:login")
    else:
        form = RegisterForm()
    return render(request, "register.html", {"form": form, "creating_admin": True})


@login_required
def page_complaint(request):
    """
    Regular user complaint page:
      - Shows the form
      - Shows complaint history for this user (most recent first)
    """
    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Complaint submitted. We’ll review it shortly.")
            # Redirect back to the same page so it shows up in history immediately
            return redirect("users:complaint")   # make sure your urls.py names this pattern 'complaint'
    else:
        form = ComplaintForm()

    items = (
        Complaint.objects
        .filter(user=request.user)
        .order_by("-created")[:10]
    )

    return render(request, "complaint.html", {"form": form, "items": items})


# =========================  Dashboard  =========================\

@login_required
def profile_view(request):
    return render(request, "profile.html")


# =========================  Auth Gate  =========================
def auth_gate(request, target):
    target_map = {
        "schedule": "users:schedule",
        "recycling": "users:recycling",
        "reuse": "users:reuse",
        "track": "users:track",
        "complaint": "users:complaint",
        "profile": "users:profile",
    }
    if not request.user.is_authenticated:
        messages.info(request, "Please create a free account to access this feature.")
        try:
            return redirect("users:signup")
        except NoReverseMatch:
            return redirect("users:login")
    dest = target_map.get(target)
    if dest:
        return redirect(dest)
    messages.error(request, "Unknown destination.")
    return redirect("users:dashboard")


@login_required
def dashboard(request):
    # Admins straight to Django Admin
    if request.user.is_superuser or (
        getattr(request.user, "role", "") == "admin" and request.user.is_staff
    ):
        return redirect("/admin/")

    # ---------------- Driver dashboard ----------------
    if getattr(request.user, "role", "") == "driver":
        DeliveryTask_m     = apps.get_model("users", "DeliveryTask",     require_ready=False)
        Complaint_m        = apps.get_model("users", "Complaint",        require_ready=False)
        DriverPointEvent_m = apps.get_model("users", "DriverPointEvent", require_ready=False)

        active = []
        history = []
        complaints = []
        points = 0

        if DeliveryTask_m:
            active = (
                DeliveryTask_m.objects.filter(assigned_to=request.user)
                .exclude(status__in=["completed", "cancelled"])
                .order_by("-created")[:20]
            )
            history = (
                DeliveryTask_m.objects
                .filter(assigned_to=request.user, status="completed")
                .order_by("-completed_at")[:20]
            )

        recent_activity = []
        for t in active[:5]:
            recent_activity.append({
                "title": f"Task — {t.address}",
                "when": _to_dhaka(getattr(t, "created", None)),
                "kind": t.status,
            })
        for t in history[:5]:
            recent_activity.append({
                "title": f"Completed — {t.address}",
                "when": _to_dhaka(getattr(t, "completed_at", None)),
                "kind": "completed",
            })
        recent_activity.sort(
            key=lambda x: x["when"] or datetime.min.replace(tzinfo=py_tz.utc),
            reverse=True,
        )

        if Complaint_m and Complaint_m.objects.filter(driver=request.user).exists():
            complaints = list(
                Complaint_m.objects.filter(driver=request.user).order_by("-created")[:20]
            )

        if DriverPointEvent_m:
            points = (
                DriverPointEvent_m.objects
                .filter(driver=request.user)
                .aggregate(total=models.Sum("points"))
                .get("total") or 0
            )

        drivers = User.objects.filter(role="driver").order_by("first_name", "username")

        return render(request, "driver.html", {
            "active": active,
            "history": history,
            "recent_activity": recent_activity,
            "complaints": complaints,
            "points": points,
            "drivers": drivers,
        })

    # ---------------- Regular user dashboard ----------------
    if getattr(request.user, "role", "") == "regular":
        today = dt_date.today()

        pickups = (
            PickupRequest.objects.filter(user=request.user)
            .order_by("-date", "-time")[:10]
        )
        upcoming_pickups = (
            PickupRequest.objects.filter(user=request.user, date__gte=today)
            .exclude(status="cancelled")
            .order_by("date", "time")[:10]
        )
        recent_pickups = (
            PickupRequest.objects.filter(user=request.user, date__lt=today)
            .order_by("-date", "-time")[:10]
        )

        RecyclingLog    = apps.get_model("users", "RecyclingLog",  require_ready=False)
        ReuseDonation_m = apps.get_model("users", "ReuseDonation", require_ready=False)
        Complaint_m     = apps.get_model("users", "Complaint",     require_ready=False)
        RewardEvent     = apps.get_model("users", "RewardEvent",   require_ready=False)

        recycling_events = []
        if RecyclingLog:
            qs = RecyclingLog.objects.filter(user=request.user)
            recycling_events = _safe_order(qs, ["-date", "-created", "-created_at", "-id"])[:10]

        reuse_donations = []
        if ReuseDonation_m:
            qs = ReuseDonation_m.objects.filter(user=request.user)
            reuse_donations = _safe_order(qs, ["-date", "-created", "-created_at", "-id"])[:10]

        # NEW: items this user accepted from the reuse market (as taker/buyer)
        reuse_taken = []
        if ReuseDonation_m:
            qs = (
                ReuseDonation_m.objects
                .filter(accepted_by=request.user)
                .exclude(user=request.user)  # don’t include their own posts
            )
            # Prefer accepted_at if present; fall back to created/id gracefully
            reuse_taken = _safe_order(qs, ["-accepted_at", "-created", "-id"])[:10]

        complaints = []
        if Complaint_m:
            qs = Complaint_m.objects.filter(user=request.user)
            complaints = _safe_order(qs, ["-date", "-created", "-created_at", "-id"])[:10]

        # decorate objects for templates
        _decorate_collections(pickups, reuse_donations, complaints)
        _decorate_collections([], reuse_taken, [])  # decorate accepted list too

        rewards_points = 0
        rewards_history = []
        if RewardEvent:
            rewards_points = (
                RewardEvent.objects.filter(user=request.user)
                .aggregate(total=models.Sum("points"))
                .get("total") or 0
            )
            rewards_history = _decorate_rewards(
                list(RewardEvent.objects.filter(user=request.user).order_by("-created")[:10])
            )

        # Recent activity — include accepted reuse items
        recent_activity = []

        for e in (recycling_events[:5] if recycling_events else []):
            recent_activity.append({
                "title": f"Recycling — {getattr(e, 'material', 'Recycling')}",
                "when": _to_dhaka(getattr(e, "created", None)),
                "kind": getattr(e, "status", "logged"),
                "photo": getattr(e, "photo", None),
                "row": _status_class(getattr(e, "status", None)),
            })

        # Add up to 2 accepted reuse entries to the feed
        for a in (reuse_taken[:10] if reuse_taken else []):
            recent_activity.append({
                "title": f"Accepted reuse — {a.item_name or a.category}",
                "when": _to_dhaka(getattr(a, "accepted_at", None) or getattr(a, "created", None)),
                "kind": "accepted",
                "photo": getattr(a, "photo", None),
                "row": "ok",
            })

        recent_activity.sort(
            key=lambda x: x["when"] or datetime.min.replace(tzinfo=py_tz.utc),
            reverse=True,
        )

        return render(request, "regular.html", {
            "pickups": pickups,
            "upcoming_pickups": upcoming_pickups,
            "recent_pickups": recent_pickups,
            "recycling_events": recycling_events,
            "reuse_donations": reuse_donations,
            "reuse_taken": reuse_taken,      # <-- expose to template (your accepted history)
            "complaints": complaints,
            "rewards_points": rewards_points,
            "rewards_history": rewards_history,
            "recent_activity": recent_activity,
        })

    messages.error(request, "Your account doesn't have a valid role.")
    return redirect("users:login")

# =========================  Feature pages  =========================
@login_required
def page_schedule(request):
    if getattr(request.user, "role", "") != "regular":
        messages.error(request, "Only regular users can schedule pickups.")
        return redirect("users:dashboard")
    if request.method == "POST":
        form = PickupRequestForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Pickup scheduled successfully!")
            return redirect("users:schedule")
    else:
        form = PickupRequestForm()
    return render(request, "schedule.html", {"form": form})


@login_required
def page_recycling(request):
    if "RecyclingForm" not in globals() or RecyclingForm is None:
        messages.error(request, "Recycling form is not available yet.")
        return redirect("users:dashboard")
    if request.method == "POST":
        form = RecyclingForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Recycling entry added.")
            return redirect("users:recycling")
    else:
        form = RecyclingForm()
    return render(request, "recycling.html", {"form": form})


@login_required
def page_reuse(request):
    if "ReuseForm" not in globals() or ReuseForm is None:
        messages.error(request, "Reuse donation form is not available yet.")
        return redirect("users:dashboard")
    if request.method == "POST":
        form = ReuseForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, "Donation recorded.")
            return redirect("users:reuse")
    else:
        form = ReuseForm()
    return render(request, "reuse.html", {"form": form})


# --- helpers for track page ---------------------------------------------------

# users/views.py

# --- delivery helpers --------------------------------------------------------

def _get_delivery_models():
    DeliveryTask   = apps.get_model("users", "DeliveryTask",   require_ready=False)
    DriverLocation = apps.get_model("users", "DriverLocation", require_ready=False)
    LocationPing   = apps.get_model("users", "LocationPing",   require_ready=False)
    return DeliveryTask, DriverLocation, LocationPing


def _latest_user_task(user):
    DeliveryTask, _, _ = _get_delivery_models()
    if not DeliveryTask:
        return None
    return (DeliveryTask.objects
            .filter(customer=user)
            .order_by("-created")
            .first())


def _status_badge_hint(status: str):
    """Badge + hint text shown on the Track page and JSON."""
    s = (status or "").lower()
    if s in {"completed", "done"}:
        return "Completed", "Pickup completed — thanks!"
    if s == "arrived":
        return "Arrived", "Driver is at your location."
    if s in {"enroute", "en_route", "en route"}:
        return "En Route", "Driver is on the way."
    if s in {"accepted", "assigned"}:
        return "Scheduled", "Soon your driver will pick your waste."
    if s == "cancelled":
        return "Cancelled", "Pickup cancelled."
    return "Pending", "Waiting to be scheduled."


# --- regular user's Track page ----------------------------------------------

@login_required
def page_track(request):

    DeliveryTask_m, DriverLocation_m, _ = _get_delivery_models()

    items, task, active_id = [], None, None
    q = request.GET.get("q")
    error_text = None

    if DeliveryTask_m:
        items = list(
            DeliveryTask_m.objects
            .filter(customer=request.user)
            .order_by("-created")[:12]
        )

        if q:
            try:
                q_int = int(q)
                task = (DeliveryTask_m.objects
                        .select_related("assigned_to", "pickup_request")
                        .get(pk=q_int, customer=request.user))
                active_id = task.id
            except ValueError:
                error_text = "Please enter a valid numeric request ID."
                messages.error(request, error_text)
                task = None
            except DeliveryTask_m.DoesNotExist:
                error_text = f"No pickup found with ID #{q}."
                messages.error(request, error_text)
                task = None
        else:
            task = _latest_user_task(request.user)
            active_id = getattr(task, "id", None)

    # Driver details and last known location
    driver_name = driver_phone = driver_email = None
    last_lat = last_lng = None
    if task and getattr(task, "assigned_to_id", None):
        d = task.assigned_to
        driver_name  = d.get_full_name() or d.username
        driver_phone = getattr(d, "phone_number", "") or ""
        driver_email = getattr(d, "email", "") or ""
        if DriverLocation_m:
            last = DriverLocation_m.objects.filter(driver_id=d.id).first()
            if last:
                last_lat = float(last.lat) if last.lat is not None else None
                last_lng = float(last.lng) if last.lng is not None else None

    status_badge = status_hint = ""
    if task:
        status_badge, status_hint = _status_badge_hint(task.status)

    # Show the pickup photo only when a specific ID was searched and a photo exists
    pickup_photo_url = None
    show_photo = False
    if q and task and getattr(task, "pickup_request", None):
        photo = getattr(task.pickup_request, "photo", None)
        if photo and getattr(photo, "url", None):
            pickup_photo_url = photo.url
            show_photo = True

    return render(request, "track.html", {
        "items": items,
        "task": task,
        "active_id": active_id,

        "driver_name": driver_name,
        "driver_phone": driver_phone,
        "driver_email": driver_email,

        "status_badge": status_badge,
        "status_hint": status_hint,

        "last_lat": last_lat,
        "last_lng": last_lng,

        "show_photo": show_photo,
        "pickup_photo_url": pickup_photo_url,

        "error_text": error_text,   # <-- handy if you also want to show a custom banner
    })

@login_required
def user_track_latest(request):
    DeliveryTask_m, DriverLocation_m, _ = _get_delivery_models()
    if not DeliveryTask_m:
        return JsonResponse({"ok": False, "error": "Tracking not available."}, status=404)

    task = _latest_user_task(request.user)
    if not task:
        return JsonResponse({"ok": False, "error": "No deliveries found."}, status=404)

    loc = None
    if DriverLocation_m and task.assigned_to_id:
        loc = DriverLocation_m.objects.filter(driver_id=task.assigned_to_id).first()

    badge, hint = _status_badge_hint(task.status)
    return JsonResponse({
        "ok": True,
        "task": {
            "id": task.id,
            "address": task.address,
            "status": task.status,
            "status_badge": badge,
            "status_hint": hint,
            "window_start": getattr(task, "window_start", None),
            "window_end": getattr(task, "window_end", None),
            "driver": ({
                "id": task.assigned_to_id,
                "name": task.assigned_to.get_full_name() or task.assigned_to.username,
                "phone": getattr(task.assigned_to, "phone_number", "") or "",
                "email": getattr(task.assigned_to, "email", "") or "",
            } if task.assigned_to_id else None),
        },
        "driver_location": ({
            "lat": float(loc.lat) if loc and loc.lat is not None else None,
            "lng": float(loc.lng) if loc and loc.lng is not None else None,
            "last_seen": loc.last_seen.isoformat() if loc and loc.last_seen else None,
        } if loc else None),
    })



@login_required
def user_track_task(request, pk: int):
    DeliveryTask_m, DriverLocation_m, _ = _get_delivery_models()
    if not DeliveryTask_m:
        return JsonResponse({"ok": False, "error": "Tracking not available."}, status=404)

    task = get_object_or_404(
        DeliveryTask_m.objects.select_related("assigned_to"),
        pk=pk, customer=request.user,
    )

    loc = None
    if DriverLocation_m and task.assigned_to_id:
        loc = DriverLocation_m.objects.filter(driver_id=task.assigned_to_id).first()

    badge, hint = _status_badge_hint(task.status)
    return JsonResponse({
        "ok": True,
        "task": {
            "id": task.id,
            "address": task.address,
            "status": task.status,
            "status_badge": badge,
            "status_hint": hint,
            "window_start": getattr(task, "window_start", None),
            "window_end": getattr(task, "window_end", None),
            "driver": ({
                "id": task.assigned_to_id,
                "name": task.assigned_to.get_full_name() or task.assigned_to.username,
                "phone": getattr(task.assigned_to, "phone_number", "") or "",
                "email": getattr(task.assigned_to, "email", "") or "",
            } if task.assigned_to_id else None),
        },
        "driver_location": ({
            "lat": float(loc.lat) if loc and loc.lat is not None else None,
            "lng": float(loc.lng) if loc and loc.lng is not None else None,
            "last_seen": loc.last_seen.isoformat() if loc and loc.last_seen else None,
        } if loc else None),
    })



# =========================  Contact  =========================
def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, "Thanks! We received your message and will reply soon."
            )
            return redirect("users:contact")
        return render(
            request,
            "contact.html",
            {"form": form, "errors": form.errors, "data": request.POST},
        )
    return render(request, "contact.html", {"form": ContactForm(), "errors": {}, "data": {}})


# =========================  Reuse Market  =========================
@login_required
@require_POST
def reuse_accept(request, pk):
    """
    Current user claims an item. Uses a conditional UPDATE so only the first click wins.
    """
    if ReuseDonation.objects.filter(pk=pk, user=request.user).exists():
        messages.warning(request, "You can’t accept your own donation.")
        return redirect("users:reuse_market")

    rows = (
        ReuseDonation.objects.filter(
            pk=pk, status__iexact="pending", accepted_by__isnull=True
        )
        .exclude(user=request.user)
        .update(
            status="accepted",
            accepted_by=request.user,
            accepted_at=timezone.now(),  # field exists in your model B choice
        )
    )

    if rows == 0:
        messages.info(request, "This item is no longer available.")
        return redirect("users:reuse_market")

    donation = get_object_or_404(ReuseDonation.objects.select_related("user"), pk=pk)
    try:
        to_email = getattr(donation.user, "email", None)
        taker_name = request.user.get_full_name() or request.user.username
        poster_name = donation.user.get_full_name() or donation.user.username
        desc = (
            getattr(donation, "item_name", None)
            or donation.description
            or donation.category
            or "your item"
        )

        if to_email:
            subj = "Your reuse item was accepted"
            body = (
                f"Hi {poster_name},\n\n"
                f"{taker_name} has accepted {desc}.\n"
                f"You can reply to this email to contact them.\n\n"
                f"— CleanTrack+"
            )
            EmailMultiAlternatives(
                subj,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [to_email],
                reply_to=[request.user.email] if request.user.email else None,
            ).send(fail_silently=True)
    except Exception:
        pass

    messages.success(request, "Accepted! The donor has been notified.")
    return redirect("users:reuse_market")


@login_required
def reuse_market(request):
    qs = ReuseDonation.objects.select_related("user", "accepted_by")
    qs = qs.annotate(
        status_rank=models.Case(
            models.When(status__iexact="pending", then=models.Value(0)),
            models.When(status__iexact="accepted", then=models.Value(1)),
            models.When(status__iexact="donated", then=models.Value(2)),
            default=models.Value(3),
            output_field=models.IntegerField(),
        )
    ).order_by("status_rank", "-created")

    items = list(qs[:120])

    for it in items:
        try:
            it.created_dhaka = _to_dhaka(getattr(it, "created", None))
        except Exception:
            it.created_dhaka = getattr(it, "created", None)

        if not getattr(it, "item_name", None):
            it.item_name = it.category or "Donation"
        if not getattr(it, "description", None):
            it.description = it.note or ""

        it.poster_email = getattr(it.user, "email", "") or ""
        it.poster_phone = getattr(it.user, "phone_number", "") or ""

        it.is_owner = it.user_id == request.user.id
        it.is_accepted_by_me = getattr(it, "accepted_by_id", None) == request.user.id
        it.can_accept = (
            (it.status or "").lower() == "pending"
            and not it.is_owner
            and getattr(it, "accepted_by_id", None) is None
        )

    return render(request, "users/reuse_market.html", {"items": items})



@login_required
def accepted_list(request):
    status = request.GET.get("status") or "accepted"

    base_qs = (ReuseDonation.objects.select_related("user", "accepted_by")
               .filter(accepted_by=request.user)
               .order_by("-accepted_at", "-created"))

    qs = base_qs
    if status in {"accepted", "completed", "cancelled"}:
        qs = qs.filter(status=status)

    # small pagination
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    # counts for tabs
    counts = {
        "accepted": base_qs.filter(status="accepted").count(),
        "completed": base_qs.filter(status="completed").count(),
        "cancelled": base_qs.filter(status="cancelled").count(),
    }

    # stats row
    agg = qs.aggregate(sum_quantity=Sum("quantity"))
    sum_quantity = agg.get("sum_quantity") or 0
    first = qs.first()
    last_accepted = (first.accepted_at or first.created) if first else None

    ctx = {
        "page_obj": page_obj,
        "status": status,
        "counts": counts,
        "total": paginator.count,
        "sum_quantity": sum_quantity,
        "last_accepted": last_accepted,
    }
    return render(request, "accepted_list.html", ctx)


@login_required
def accepted_mark_complete(request, pk: int):
    if request.method != "POST":
        return HttpResponseForbidden()
    it = get_object_or_404(ReuseDonation, pk=pk, accepted_by=request.user)
    it.status = "completed"
    it.save(update_fields=["status"])
    messages.success(request, "Marked as collected. 🎉")
    return redirect(request.META.get("HTTP_REFERER") or "users:accepted_list")


@login_required
def accepted_cancel(request, pk: int):
    if request.method != "POST":
        return HttpResponseForbidden()
    it = get_object_or_404(ReuseDonation, pk=pk, accepted_by=request.user)
    # Free it back to the market
    it.status = "open"
    it.accepted_by = None
    it.accepted_at = None
    it.save(update_fields=["status", "accepted_by", "accepted_at"])
    messages.success(request, "Acceptance cancelled. The item is available again.")
    return redirect("users:accepted_list")


def is_driver(u):
    return u.is_authenticated and getattr(u, "role", "") == "driver"

def is_staff_user(u):
    return u.is_authenticated and (u.is_staff or u.is_superuser)

# ---------------- Dashboard ----------------

@login_required
@user_passes_test(is_driver)
def driver_dashboard(request):

    recent_tasks = (
        DeliveryTask.objects
        .filter(assigned_to=request.user)
        .exclude(status__in=[DeliveryTask.Status.COMPLETED, DeliveryTask.Status.CANCELLED])
        .order_by("-created")[:20]
    )

    # Completed tasks
    completed = (
        DeliveryTask.objects
        .filter(assigned_to=request.user, status=DeliveryTask.Status.COMPLETED)
        .order_by("-completed_at", "-created")[:20]
    )

    # Points history and total
    rewards = (
        DriverPointEvent.objects
        .filter(driver=request.user)
        .order_by("-created")[:20]
    )
    reward_total = (
        DriverPointEvent.objects
        .filter(driver=request.user)
        .aggregate(total=Sum("points"))
        .get("total") or 0
    )

    # Driver's own complaints
    complaints = (
        DriverComplaint.objects
        .filter(driver=request.user)
        .order_by("-when_dt")[:20]
    )

    # Recent activity (10)
    activity = (
        DriverActivity.objects
        .filter(driver=request.user)
        .order_by("-when", "-id")[:10]
    )

    return render(
        request,
        "driver.html",
        {
            "recent_tasks": recent_tasks,   # used by "Recent tasks" card
            "completed": completed,         # used by "Completed tasks" card
            "rewards": rewards,             # used by "Rewards" list
            "reward_total": reward_total,   # ring fill
            "complaints": complaints,       # complaint history
            "activity": activity,           # recent activity card
        },
    )


@login_required
@user_passes_test(is_driver)
def driver_tasks(request):
    """Full list of the driver’s tasks split by section."""
    qs = DeliveryTask.objects.filter(assigned_to=request.user).order_by("-created")
    open_tasks = qs.exclude(status__in=[DeliveryTask.Status.COMPLETED, DeliveryTask.Status.CANCELLED])[:100]
    completed = qs.filter(status=DeliveryTask.Status.COMPLETED)[:100]
    cancelled = qs.filter(status=DeliveryTask.Status.CANCELLED)[:100]
    return render(
        request,
        "driver_tasks.html",
        {"open_tasks": open_tasks, "completed": completed, "cancelled": cancelled},
    )

# ---------------- Task state actions ----------------

def _get_task_for_driver_or_404(user, pk: int) -> DeliveryTask:
    return get_object_or_404(
        DeliveryTask.objects.select_related("customer"),
        pk=pk,
        assigned_to=user,
    )

@login_required
@user_passes_test(is_driver)
def driver_task_start(request, pk: int):
    if request.method != "POST":
        return HttpResponseForbidden()
    t = _get_task_for_driver_or_404(request.user, pk)
    t.status = DeliveryTask.Status.ENROUTE
    t.started_at = timezone.now()
    t.save(update_fields=["status", "started_at"])
    messages.success(request, "Marked as En Route.")
    return redirect("users:driver_tasks")

@login_required
@user_passes_test(is_driver)
def driver_task_arrive(request, pk: int):
    if request.method != "POST":
        return HttpResponseForbidden()
    t = _get_task_for_driver_or_404(request.user, pk)
    t.status = DeliveryTask.Status.ARRIVED
    t.arrived_at = timezone.now()
    t.save(update_fields=["status", "arrived_at"])
    messages.success(request, "Marked as Arrived.")
    return redirect("users:driver_tasks")

@login_required
@user_passes_test(is_driver)
def driver_task_complete(request, pk: int):
    if request.method != "POST":
        return HttpResponseForbidden()
    t = _get_task_for_driver_or_404(request.user, pk)
    t.status = DeliveryTask.Status.COMPLETED
    t.completed_at = timezone.now()
    t.save(update_fields=["status", "completed_at"])

    # Award points (safe if already has helper)
    try:
        t.award_points(request.user, 10, reason="delivery")
    except Exception:
        pass

    messages.success(request, "Great job! Task completed and points added.")
    return redirect("users:driver_tasks")

# ---------------- Live location ping (accepts JSON or form) ----------------

@login_required
@user_passes_test(is_driver)
def driver_ping(request):
    """Accept JSON {lat, lng, task_id?} OR form-encoded POST."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "err": "POST required"}, status=405)

    lat = lng = task_id = None
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception:
            return JsonResponse({"ok": False, "err": "invalid JSON"}, status=400)
        lat, lng, task_id = data.get("lat"), data.get("lng"), data.get("task_id")
    else:
        lat, lng, task_id = request.POST.get("lat"), request.POST.get("lng"), request.POST.get("task_id")

    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "err": "invalid lat/lng"}, status=400)

    task = None
    if task_id:
        try:
            task = DeliveryTask.objects.get(pk=int(task_id), assigned_to=request.user)
        except DeliveryTask.DoesNotExist:
            task = None  # ignore

    loc, _ = DriverLocation.objects.get_or_create(driver=request.user)
    loc.lat = lat
    loc.lng = lng
    loc.last_seen = timezone.now()
    loc.save(update_fields=["lat", "lng", "last_seen"])

    LocationPing.objects.create(driver=request.user, task=task, lat=lat, lng=lng)
    return JsonResponse({"ok": True})

# ---------------- Profile / Forum / Activity / Complaint ----------------

@login_required
@user_passes_test(is_driver)
def driver_profile(request):
    return render(request, "driver_profile.html", {"driver": request.user})

@login_required
@user_passes_test(is_driver)
def driver_forum(request):
    drivers = User.objects.filter(role="driver").order_by("first_name", "username")
    return render(request, "driver_forum.html", {"drivers": drivers})

@login_required
@user_passes_test(is_driver)
def driver_activity(request):
    items = DriverActivity.objects.filter(driver=request.user).order_by("-when", "-id")[:50]
    return render(request, "driver_activity.html", {"items": items})

@login_required
@user_passes_test(is_driver)
def driver_complaint(request):
    if request.method == "POST":
        form = DriverComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.driver = request.user
            obj.save()
            messages.success(request, "Complaint submitted.")
            return redirect("users:driver_complaint")
    else:
        form = DriverComplaintForm()
    return render(request, "driver_complaint.html", {"form": form})

@login_required
def track_task(request, pk):
    t = get_object_or_404(
        DeliveryTask.objects.select_related("customer", "assigned_to"), pk=pk
    )
    if not (
        request.user.is_staff
        or request.user.is_superuser
        or request.user == t.customer
        or request.user == t.assigned_to
    ):
        return HttpResponseForbidden("Not allowed")

    last = DriverLocation.objects.filter(driver=t.assigned_to).first()
    return render(
        request,
        "track_task.html",
        {"task": t, "last_lat": getattr(last, "lat", None), "last_lng": getattr(last, "lng", None)},
    )


@login_required
def task_positions_api(request, pk):
    t = get_object_or_404(DeliveryTask, pk=pk)
    if not (
        request.user.is_staff
        or request.user.is_superuser
        or request.user == t.customer
        or request.user == t.assigned_to
    ):
        return HttpResponseForbidden()

    p = (
        LocationPing.objects.filter(driver=t.assigned_to, task=t)
        .order_by("-created")
        .first()
    )
    if not p:
        return JsonResponse({"ok": True, "pos": None})
    return JsonResponse(
        {
            "ok": True,
            "pos": {"lat": float(p.lat), "lng": float(p.lng), "ts": p.created.isoformat()},
        }
    )

@require_POST
def home_contact_submit(request):

    form = ContactForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Thanks! Your message has been sent.")
    else:
        messages.error(request, "Please fix the errors and try again.")
    return redirect("home")