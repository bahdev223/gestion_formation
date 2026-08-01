from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .access import PERMISSION_CHOICES, ROLE_PERMISSIONS
from .models import InvitationOrganisation, MembreOrganisation, Organisation

FIELD_CLASS = (
    "w-full rounded-md border border-slate-300 bg-white px-3 py-2.5 text-sm "
    "outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
)


class PermissionFieldsMixin:
    def add_permission_fields(self, initial_permissions=None):
        initial_permissions = initial_permissions or {}
        role = self.initial.get("role") or getattr(self.instance, "role", None)
        defaults = ROLE_PERMISSIONS.get(role, set())
        for code, label in PERMISSION_CHOICES:
            name = f"permission__{code}"
            self.fields[name] = forms.BooleanField(
                label=label,
                required=False,
                initial=initial_permissions.get(code, code in defaults),
            )

    def cleaned_permissions(self):
        role = self.cleaned_data.get("role")
        defaults = ROLE_PERMISSIONS.get(role, set())
        overrides = {}
        for code, _ in PERMISSION_CHOICES:
            value = bool(self.cleaned_data.get(f"permission__{code}"))
            if value != (code in defaults):
                overrides[code] = value
        return overrides


class InvitationOrganisationForm(PermissionFieldsMixin, forms.ModelForm):
    class Meta:
        model = InvitationOrganisation
        fields = ["email", "role"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial.setdefault("role", MembreOrganisation.Role.RESPONSABLE)
        self.fields["email"].widget.attrs.update({"class": FIELD_CLASS, "placeholder": "collaborateur@entreprise.com"})
        self.fields["role"].widget.attrs["class"] = FIELD_CLASS
        self.add_permission_fields()

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class MembreOrganisationForm(PermissionFieldsMixin, forms.ModelForm):
    class Meta:
        model = MembreOrganisation
        fields = ["role", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].widget.attrs["class"] = FIELD_CLASS
        self.fields["is_active"].label = "Acces actif"
        self.add_permission_fields(self.instance.permissions_personnalisees)


class InvitationAcceptForm(forms.Form):
    first_name = forms.CharField(label="Prenom", max_length=150)
    last_name = forms.CharField(label="Nom", max_length=150)
    matricule = forms.CharField(label="Matricule de connexion", max_length=150)
    password1 = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmer le mot de passe", widget=forms.PasswordInput)

    def __init__(self, *args, email=None, **kwargs):
        self.email = email
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = FIELD_CLASS

    def clean_matricule(self):
        value = self.cleaned_data["matricule"].strip()
        if get_user_model().objects.filter(username__iexact=value).exists():
            raise forms.ValidationError("Ce matricule est deja utilise.")
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "Les mots de passe ne correspondent pas.")
        password = cleaned.get("password1")
        if password:
            try:
                password_validation.validate_password(password)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned


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
