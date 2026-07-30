from django import forms
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from .models import Organisation


class OrganisationSignupForm(forms.Form):
    organisation_nom = forms.CharField(label="Nom de l'entreprise", max_length=255)
    organisation_email = forms.EmailField(label="Email de l'entreprise")
    organisation_telephone = forms.CharField(label="Téléphone de l'entreprise", max_length=30)
    ville = forms.CharField(label="Ville", max_length=150, required=False)
    pays = forms.CharField(label="Pays", max_length=100, initial="Mali")

    first_name = forms.CharField(label="Prénom", max_length=150)
    last_name = forms.CharField(label="Nom", max_length=150)
    email = forms.EmailField(label="Email de connexion")
    matricule = forms.CharField(
        label="Matricule de connexion",
        max_length=150,
        help_text="Ce matricule permet aussi de se connecter.",
    )
    password1 = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmer le mot de passe", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "w-full rounded-md border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-[var(--baly-blue)] focus:ring-2 focus:ring-blue-100",
            )

    def clean_organisation_nom(self):
        value = self.cleaned_data["organisation_nom"].strip()
        base_slug = slugify(value)
        if Organisation.objects.filter(slug=base_slug).exists():
            raise forms.ValidationError("Une entreprise avec ce nom existe déjà.")
        return value

    def clean_email(self):
        value = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=value).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")
        return value

    def clean_matricule(self):
        value = self.cleaned_data["matricule"].strip()
        if get_user_model().objects.filter(username__iexact=value).exists():
            raise forms.ValidationError("Ce matricule est déjà utilisé.")
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "Les mots de passe ne correspondent pas.")
        return cleaned
