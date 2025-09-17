
from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

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
