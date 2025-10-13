from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils import timezone

from .models import PickupRequest, RecyclingLog, ReuseDonation, Complaint, ContactMessage
from .models import DriverComplaint

User = get_user_model()

PUBLIC_ROLE_CHOICES = (
    ("regular", "Regular"),
    ("driver",  "Driver"),
)

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=PUBLIC_ROLE_CHOICES, required=True)
    phone_number = forms.CharField(required=True, max_length=11)

    class Meta:
        model = User
        fields = ["username", "email", "role", "phone_number", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = self.cleaned_data["role"]
        user.phone_number = self.cleaned_data["phone_number"]
        if commit:
            user.save()
        return user


class LoginEmailOrUsernameForm(AuthenticationForm):
    def clean(self):
        login_id = (self.data.get("username") or "").strip()
        password = self.data.get("password") or ""
        user = authenticate(self.request, username=login_id, password=password)
        if user is None:
            try:
                u = User.objects.get(email__iexact=login_id)
                user = authenticate(self.request, username=u.get_username(), password=password)
            except User.DoesNotExist:
                user = None

        if user is None:
            raise self.get_invalid_login_error()
        self.confirm_login_allowed(user)
        self.user_cache = user
        self.cleaned_data = {"username": login_id, "password": password}
        return self.cleaned_data


class PickupRequestForm(forms.ModelForm):
    class Meta:
        model = PickupRequest
        fields = ["date", "time", "address", "notes", "photo", "waste_type"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "id": "id_date", "placeholder": " "}),
            "time": forms.TimeInput(attrs={"type": "time", "id": "id_time", "placeholder": " "}),
            "address": forms.TextInput(attrs={"id": "id_address", "placeholder": "House/Street, City"}),
            "notes": forms.Textarea(attrs={"id": "id_notes", "rows": 4, "placeholder": "Any special instructions?"}),
        }

    # NEW: set HTML min (blocks past dates in native pickers)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today_iso = timezone.localdate().isoformat()
        self.fields["date"].widget.attrs.setdefault("min", today_iso)

    # NEW: server-side guard (works even if JS/HTML is bypassed)
    def clean_date(self):
        d = self.cleaned_data.get("date")
        if d and d < timezone.localdate():
            raise forms.ValidationError("Please choose today or a future date.")
        return d

    def clean_waste_type(self):
        val = self.cleaned_data.get("waste_type") or self.data.get("waste_type")
        # fall back safely if not in choices
        if not val or val not in dict(PickupRequest.WASTE_TYPES):
            return "regular"
        return val


class ContactForm(forms.ModelForm):
    hp = forms.CharField(required=False, widget=forms.TextInput(attrs={"autocomplete": "off"}))  # honeypot

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name":    forms.TextInput(attrs={"placeholder": "Your full name", "autocomplete": "name", "aria-label": "Your name"}),
            "email":   forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email", "aria-label": "Email address"}),
            "subject": forms.TextInput(attrs={"placeholder": "What is this about? (optional)", "aria-label": "Subject"}),
            "message": forms.Textarea(attrs={"rows": 6, "placeholder": "Write your message…", "aria-label": "Message"}),
        }

    def clean_hp(self):
        if self.cleaned_data.get("hp"):
            raise forms.ValidationError("Spam detected.")
        return ""


class RecyclingForm(forms.ModelForm):
    class Meta:
        model = RecyclingLog
        fields = ["material", "weight_kg", "note", "photo"]
        widgets = {
            "material": forms.TextInput(attrs={"placeholder": "e.g., Mixed paper, Plastic #1-2"}),
            "weight_kg": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "0.00"}),
            "note": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional note"}),
        }

    def clean_weight_kg(self):
        w = self.cleaned_data.get("weight_kg")
        if w is None:
            return w
        if w < 0:
            raise forms.ValidationError("Weight cannot be negative.")
        return w


class ReuseForm(forms.ModelForm):
    class Meta:
        model = ReuseDonation
        fields = ["category", "quantity", "partner", "note", "photo"]
        widgets = {
            "category": forms.TextInput(attrs={"placeholder": "e.g., Furniture, Toys, Kitchen set, Anything!"}),
            "quantity": forms.NumberInput(attrs={"min": "1", "step": "1"}),
            "partner": forms.TextInput(attrs={"placeholder": "Optional partner/org"}),
            "note": forms.TextInput(attrs={"placeholder": "Pickup instructions, condition, etc."}),
        }

    def clean_quantity(self):
        q = self.cleaned_data.get("quantity")
        if q is not None and q <= 0:
            raise forms.ValidationError("Quantity must be at least 1.")
        return q


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["complaint_type", "subject", "description", "photo"]
        widgets = {
            "complaint_type": forms.TextInput(attrs={
                "placeholder": "Category (e.g., Service, Billing, Pickup delay)"
            }),
            "subject": forms.TextInput(attrs={
                "placeholder": "Short subject"
            }),
            "description": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Describe the issue…"
            }),
        }
        labels = {
            "complaint_type": "Category",
        }


class DriverComplaintForm(forms.ModelForm):
    class Meta:
        model = DriverComplaint
        fields = ["against_user","category","description","address","photo"]
        widgets = {
            "description": forms.Textarea(attrs={"rows":4}),
        }
