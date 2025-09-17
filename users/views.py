
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .forms import RegisterForm, LoginEmailOrUsernameForm
from .tokens import account_activation_token

User = get_user_model()

class RoleLoginView(LoginView):
    template_name = "login.html"
    authentication_form = LoginEmailOrUsernameForm
    redirect_authenticated_user = False

    def get_success_url(self):
        u = self.request.user
        if u.is_superuser or (getattr(u, "role", "") == "admin" and u.is_staff):
            return "/admin/"
        return reverse("users:dashboard")

def _build_activation_url(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)
    path = reverse("users:activate", kwargs={"uidb64": uid, "token": token})
    if getattr(settings, "SITE_DOMAIN", None):
        return f"{settings.SITE_DOMAIN}{path}"
    return request.build_absolute_uri(path)

def _send_activation_email(request, user):
    activate_url = _build_activation_url(request, user)
    ctx = {"user": user, "activate_url": activate_url}
    subject = "Activate your CleanTrack account"
    text_body = render_to_string("users/activation_email.txt", ctx)
    html_body = render_to_string("users/activation_email.html", ctx)
    msg = EmailMultiAlternatives(subject, text_body, settings.DEFAULT_FROM_EMAIL, [user.email])
    msg.attach_alternative(html_body, "text/html")
    msg.send()

def signup_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            _send_activation_email(request, user)
            messages.success(request, "We emailed you an activation link. Please verify to log in.")
            return redirect("users:login")
    else:
        form = RegisterForm()
    return render(request, "register.html", {"form": form})

def activate(request, uidb64, token):
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
def dashboard(request):
    if request.user.is_superuser or (getattr(request.user, "role", "") == "admin" and request.user.is_staff):
        return redirect("/admin/")
    if request.user.role == "driver":
        return render(request, "driver.html")
    if request.user.role == "regular":
        return render(request, "regular.html")
    messages.error(request, "Your account doesn't have a valid role.")
    return redirect("users:login")
