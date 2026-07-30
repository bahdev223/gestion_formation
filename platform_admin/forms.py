from django import forms
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from organisations.models import Organisation
from subscriptions.models import Abonnement, PaiementAbonnement, PlanAbonnement

from .models import (
    Announcement,
    FeatureFlag,
    MaintenanceWindow,
    SupportTicket,
)

FIELD_CLASS = (
    "w-full border border-slate-300 bg-white px-3 py-2.5 text-sm "
    "text-slate-900 outline-none focus:border-cyan-600 focus:ring-2 "
    "focus:ring-cyan-100"
)


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = FIELD_CLASS


class PlatformOrganisationCreateForm(forms.Form):
    class Activation(models.TextChoices):
        ESSAI = "ESSAI", "Période d’essai"
        PAYE = "PAYE", "Abonnement payé"

    organisation_nom = forms.CharField(label="Nom de l’entreprise", max_length=255)
    organisation_email = forms.EmailField(label="Email de l’entreprise")
    organisation_telephone = forms.CharField(
        label="Téléphone de l’entreprise",
        max_length=30,
    )
    logo = forms.ImageField(label="Logo", required=False)
    adresse = forms.CharField(
        label="Adresse",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )
    ville = forms.CharField(label="Ville", max_length=150, required=False)
    pays = forms.CharField(label="Pays", max_length=100, initial="Mali")

    owner_first_name = forms.CharField(label="Prénom du propriétaire", max_length=150)
    owner_last_name = forms.CharField(label="Nom du propriétaire", max_length=150)
    owner_email = forms.EmailField(label="Email de connexion")
    owner_telephone = forms.CharField(
        label="Téléphone du propriétaire",
        max_length=30,
        required=False,
    )
    owner_matricule = forms.CharField(
        label="Matricule de connexion",
        max_length=150,
        required=False,
        help_text="Laissez vide pour le générer automatiquement.",
    )
    owner_password = forms.CharField(
        label="Mot de passe temporaire",
        required=False,
        min_length=8,
        widget=forms.PasswordInput(render_value=True),
        help_text="Laissez vide pour générer un mot de passe sécurisé.",
    )
    envoyer_identifiants = forms.BooleanField(
        label="Envoyer le lien et les accès au propriétaire par email",
        required=False,
        initial=True,
    )

    plan = forms.ModelChoiceField(
        label="Plan",
        queryset=PlanAbonnement.objects.none(),
    )
    cycle = forms.ChoiceField(label="Cycle", choices=Abonnement.Cycle.choices)
    activation = forms.ChoiceField(label="Activation", choices=Activation.choices)
    jours_essai = forms.IntegerField(
        label="Durée de l’essai (jours)",
        min_value=1,
        max_value=365,
        initial=14,
        required=False,
    )
    montant_paye = forms.DecimalField(
        label="Montant encaissé",
        min_value=0,
        max_digits=12,
        decimal_places=2,
        required=False,
    )
    mode_paiement = forms.ChoiceField(
        label="Mode de paiement",
        choices=[
            ("", "Sélectionner"),
            ("ESPECES", "Espèces"),
            ("VIREMENT", "Virement bancaire"),
            ("MOBILE_MONEY", "Mobile Money"),
            ("CHEQUE", "Chèque"),
            ("AUTRE", "Autre"),
        ],
        required=False,
    )
    reference_paiement = forms.CharField(
        label="Référence externe",
        max_length=100,
        required=False,
    )
    notes = forms.CharField(
        label="Notes internes",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plan"].queryset = PlanAbonnement.objects.filter(is_active=True)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = FIELD_CLASS

    def clean_organisation_nom(self):
        value = self.cleaned_data["organisation_nom"].strip()
        if Organisation.objects.filter(nom__iexact=value).exists():
            raise forms.ValidationError("Une entreprise avec ce nom existe déjà.")
        return value

    def clean_owner_email(self):
        value = self.cleaned_data["owner_email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=value).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")
        return value

    def clean_owner_matricule(self):
        value = self.cleaned_data["owner_matricule"].strip()
        if value and get_user_model().objects.filter(username__iexact=value).exists():
            raise forms.ValidationError("Ce matricule est déjà utilisé.")
        return value

    def clean_reference_paiement(self):
        value = self.cleaned_data["reference_paiement"].strip()
        if value and PaiementAbonnement.objects.filter(reference=value).exists():
            raise forms.ValidationError("Cette référence de paiement existe déjà.")
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("activation") == self.Activation.PAYE:
            if cleaned.get("montant_paye") is None:
                self.add_error("montant_paye", "Indiquez le montant encaissé.")
            if not cleaned.get("mode_paiement"):
                self.add_error("mode_paiement", "Sélectionnez le mode de paiement.")
        return cleaned


class ManualSubscriptionPaymentForm(forms.Form):
    plan = forms.ModelChoiceField(
        label="Plan",
        queryset=PlanAbonnement.objects.none(),
    )
    cycle = forms.ChoiceField(label="Cycle", choices=Abonnement.Cycle.choices)
    montant = forms.DecimalField(
        label="Montant reçu",
        min_value=0,
        max_digits=12,
        decimal_places=2,
    )
    mode_paiement = forms.ChoiceField(
        label="Mode de paiement",
        choices=[
            ("ESPECES", "Espèces"),
            ("VIREMENT", "Virement bancaire"),
            ("MOBILE_MONEY", "Mobile Money"),
            ("CHEQUE", "Chèque"),
            ("AUTRE", "Autre"),
        ],
    )
    date_paiement = forms.DateTimeField(
        label="Date du paiement",
        initial=timezone.now,
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={"type": "datetime-local"},
        ),
    )
    reference = forms.CharField(
        label="Référence externe",
        max_length=100,
        required=False,
    )
    notes = forms.CharField(
        label="Justificatif ou notes",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, abonnement=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.abonnement = abonnement
        self.fields["plan"].queryset = PlanAbonnement.objects.filter(is_active=True)
        if abonnement and not self.is_bound:
            self.initial.update(
                {
                    "plan": abonnement.plan,
                    "cycle": abonnement.cycle,
                    "montant": abonnement.montant,
                }
            )
        for field in self.fields.values():
            field.widget.attrs["class"] = FIELD_CLASS

    def clean_reference(self):
        value = self.cleaned_data["reference"].strip()
        if value and PaiementAbonnement.objects.filter(reference=value).exists():
            raise forms.ValidationError("Cette référence de paiement existe déjà.")
        return value


class SupportTicketUpdateForm(StyledModelForm):
    class Meta:
        model = SupportTicket
        fields = ["priorite", "statut", "responsable"]


class FeatureFlagForm(StyledModelForm):
    class Meta:
        model = FeatureFlag
        fields = [
            "code",
            "nom",
            "description",
            "is_enabled_globally",
            "rollout_percentage",
            "organisations",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "organisations": forms.SelectMultiple(attrs={"size": 8}),
        }


class MaintenanceWindowForm(StyledModelForm):
    class Meta:
        model = MaintenanceWindow
        fields = [
            "titre",
            "message",
            "starts_at",
            "ends_at",
            "statut",
            "bloque_inscriptions",
            "affiche_banniere",
        ]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3}),
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class AnnouncementForm(StyledModelForm):
    class Meta:
        model = Announcement
        fields = [
            "titre",
            "message",
            "audience",
            "niveau",
            "is_active",
            "starts_at",
            "ends_at",
        ]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3}),
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
