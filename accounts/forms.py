from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm


class EmailOrMatriculeAuthenticationForm(AuthenticationForm):
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


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_class = (
            "w-full border border-slate-300 bg-white px-4 py-3 text-sm "
            "outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
        )
        for field in self.fields.values():
            field.widget.attrs["class"] = field_class
