# users/tokens.py
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import timezone

class ActivationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}"

account_activation_token = ActivationTokenGenerator()
