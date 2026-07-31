from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.cache import cache
from django.core.exceptions import ValidationError


class EmailOrMatriculeAuthenticationForm(AuthenticationForm):
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_SECONDS = 300

    username = forms.CharField(
        label="Email ou matricule",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "autocomplete": "username",
                "placeholder": "email@entreprise.com ou matricule",
            }
        ),
    )

    def get_client_key(self):
        request = getattr(self, "request", None)
        if not request:
            return "login-attempts:anonymous"
        ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
        return f"login-attempts:{ip}"

    def _throttle_key(self):
        return f"{self.get_client_key()}:count"

    def _check_throttling(self):
        attempts = cache.get(self._throttle_key(), 0) or 0
        if attempts >= self.MAX_LOGIN_ATTEMPTS:
            raise ValidationError(
                "Trop de tentatives. Réessayez dans quelques minutes."
            )

    def _register_failure(self):
        key = self._throttle_key()
        attempts = cache.get(key, 0) or 0
        cache.set(key, attempts + 1, timeout=self.LOCKOUT_SECONDS)

    def _clear_throttle(self):
        cache.delete(self._throttle_key())

    def clean(self):
        self._check_throttling()
        try:
            data = super().clean()
        except ValidationError:
            self._register_failure()
            raise
        self._clear_throttle()
        return data


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_class = (
            "w-full border border-slate-300 bg-white px-4 py-3 text-sm "
            "outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = field_class
