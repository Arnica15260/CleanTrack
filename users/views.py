# users/views.py
from datetime import date as dt_date, datetime, timedelta, timezone as py_tz
from zoneinfo import ZoneInfo

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse, NoReverseMatch
from django.utils import timezone

from .forms import RegisterForm, LoginEmailOrUsernameForm, PickupRequestForm, ContactForm, RecyclingForm, ReuseForm, \
    ComplaintForm
from .tokens import account_activation_token
from .models import ContactMessage, PickupRequest

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
                settings.DEFAULT_FROM_EMAIL, [user.email]
            )
            msg.attach_alternative(
                render_to_string("users/activation_email.html", ctx), "text/html"
            )
            msg.send()
            messages.success(request, "We emailed you an activation link. Please verify to log in.")
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

# =========================  Dashboard  =========================
@login_required
def dashboard(request):
    if request.user.is_superuser or (getattr(request.user, "role", "") == "admin" and request.user.is_staff):
        return redirect("/admin/")
    if getattr(request.user, "role", "") == "driver":
        return render(request, "driver.html")

    if getattr(request.user, "role", "") == "regular":
        today = dt_date.today()

        pickups = PickupRequest.objects.filter(user=request.user).order_by("-date", "-time")[:10]
        upcoming_pickups = (
            PickupRequest.objects.filter(user=request.user, date__gte=today)
            .exclude(status="cancelled")
            .order_by("date", "time")[:10]
        )
        recent_pickups = (
            PickupRequest.objects.filter(user=request.user, date__lt=today)
            .order_by("-date", "-time")[:10]
        )

        RecyclingLog  = apps.get_model("users", "RecyclingLog",  require_ready=False)
        ReuseDonation = apps.get_model("users", "ReuseDonation", require_ready=False)
        Complaint     = apps.get_model("users", "Complaint",     require_ready=False)
        RewardEvent   = apps.get_model("users", "RewardEvent",   require_ready=False)

        recycling_events = []
        if RecyclingLog:
            qs = RecyclingLog.objects.filter(user=request.user)
            recycling_events = _safe_order(qs, ["-date", "-created", "-created_at", "-id"])[:10]

        reuse_donations = []
        if ReuseDonation:
            qs = ReuseDonation.objects.filter(user=request.user)
            reuse_donations = _safe_order(qs, ["-date", "-created", "-created_at", "-id"])[:10]

        complaints = []
        if Complaint:
            qs = Complaint.objects.filter(user=request.user)
            complaints = _safe_order(qs, ["-date", "-created", "-created_at", "-id"])[:10]

        _decorate_collections(pickups, reuse_donations, complaints)

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

        # Recent activity list
        recent_activity = []
        for p in pickups[:5]:
            recent_activity.append({
                "title": f"Pickup — {p.address or 'Address'}",
                "when": p.when_dt,
                "kind": p.status or "scheduled",
                "photo": getattr(p, "photo", None),
                "row": p.row_class,
            })
        for e in (recycling_events[:3] if recycling_events else []):
            recent_activity.append({
                "title": f"Recycling — {getattr(e, 'material', 'Recycling')}",
                "when": _to_dhaka(getattr(e, "created", None)),
                "kind": getattr(e, "status", "logged"),
                "photo": getattr(e, "photo", None),
                "row": _status_class(getattr(e, "status", None)),
            })
        for c in (complaints[:2] if complaints else []):
            recent_activity.append({
                "title": f"Complaint — {c.category}",
                "when": c.when_dt,
                "kind": getattr(c, "status", "open"),
                "photo": getattr(c, "photo", None),
                "row": c.row_class,
            })
        recent_activity.sort(key=lambda x: x["when"] or datetime.min.replace(tzinfo=py_tz.utc), reverse=True)

        return render(request, "regular.html", {
            "pickups": pickups,
            "upcoming_pickups": upcoming_pickups,
            "recent_pickups": recent_pickups,
            "recycling_events": recycling_events,
            "reuse_donations": reuse_donations,
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
            obj = form.save(commit=False); obj.user = request.user; obj.save()
            messages.success(request, "Pickup scheduled successfully!")
            return redirect("users:schedule")
    else:
        form = PickupRequestForm()
    return render(request, "schedule.html", {"form": form})

@login_required
def page_recycling(request):
    if 'RecyclingForm' not in globals() or RecyclingForm is None:
        messages.error(request, "Recycling form is not available yet.")
        return redirect("users:dashboard")
    if request.method == "POST":
        form = RecyclingForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False); obj.user = request.user; obj.save()
            messages.success(request, "Recycling entry added.")
            return redirect("users:recycling")
    else:
        form = RecyclingForm()
    return render(request, "recycling.html", {"form": form})

@login_required
def page_reuse(request):
    if 'ReuseForm' not in globals() or ReuseForm is None:
        messages.error(request, "Reuse donation form is not available yet.")
        return redirect("users:dashboard")
    if request.method == "POST":
        form = ReuseForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False); obj.user = request.user; obj.save()
            messages.success(request, "Donation recorded.")
            return redirect("users:reuse")
    else:
        form = ReuseForm()
    return render(request, "reuse.html", {"form": form})

@login_required
def page_complaint(request):
    if 'ComplaintForm' not in globals() or ComplaintForm is None:
        messages.error(request, "Complaint form is not available yet.")
        return redirect("users:dashboard")
    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False); obj.user = request.user; obj.save()
            messages.success(request, "Complaint submitted. We’ll review it shortly.")
            return redirect("users:complaint")
    else:
        form = ComplaintForm()
    return render(request, "complaint.html", {"form": form})

@login_required
def page_track(request):
    return render(request, "track.html")

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

# =========================  Contact  =========================
def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thanks! We received your message and will reply soon.")
            return redirect("users:contact")
        return render(request, "contact.html", {"form": form, "errors": form.errors, "data": request.POST})
    return render(request, "contact.html", {"form": ContactForm(), "errors": {}, "data": {}})
