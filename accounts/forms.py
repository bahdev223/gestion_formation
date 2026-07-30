from django import forms
from django.contrib.auth.forms import AuthenticationForm


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
