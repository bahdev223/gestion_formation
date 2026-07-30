from decimal import Decimal

from django import forms
from django.utils import timezone

from formations.models import SessionFormation
from participants.models import Participant

from .models import Inscription


class InscriptionForm(forms.ModelForm):
    class Meta:
        model = Inscription
        fields = [
            "participant",
            "session",
            "date_inscription",
            "remise",
            "statut",
            "entreprise_payeur",
            "reference_externe",
            "observations",
        ]
        labels = {
            "date_inscription": "Date d’inscription",
            "remise": "Remise (FCFA)",
            "entreprise_payeur": "Entreprise payeuse",
            "reference_externe": "Référence externe",
        }
        widgets = {
            "date_inscription": forms.DateInput(attrs={"type": "date"}),
            "remise": forms.NumberInput(attrs={"min": 0, "step": 500}),
            "observations": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        organisation = kwargs.pop("organisation", None)
        super().__init__(*args, **kwargs)
        participants = Participant.objects.filter(
            statut=Participant.Statut.ACTIF
        )
        if organisation:
            participants = participants.filter(organisation=organisation)
        self.fields["participant"].queryset = participants.order_by("nom", "prenom")
        sessions = SessionFormation.objects.exclude(
            statut__in=[
                SessionFormation.Statut.ANNULEE,
                SessionFormation.Statut.TERMINEE,
            ]
        ).select_related("formation")
        if organisation:
            sessions = sessions.filter(organisation=organisation)
        self.fields["session"].queryset = sessions.order_by("-date_debut")

        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full border border-slate-300 bg-white px-3.5 py-3 text-sm "
                "text-slate-900 outline-none transition focus:border-blue-600 "
                "focus:ring-2 focus:ring-blue-100"
            )

    def clean(self):
        cleaned_data = super().clean()
        participant = cleaned_data.get("participant")
        session = cleaned_data.get("session")
        remise = cleaned_data.get("remise") or Decimal("0")

        if session and remise > session.prix_applique:
            self.add_error(
                "remise", "La remise ne peut pas dépasser le prix de la session."
            )

        if participant and session:
            inscription_existante = Inscription.objects.filter(
                participant=participant,
                session=session,
            ).exclude(statut=Inscription.Statut.ANNULE)
            if self.instance.pk:
                inscription_existante = inscription_existante.exclude(
                    pk=self.instance.pk
                )
            if inscription_existante.exists():
                self.add_error(
                    "participant",
                    "Ce participant est déjà inscrit à cette session.",
                )
            inscriptions_actives = session.inscriptions.exclude(
                statut=Inscription.Statut.ANNULE
            )
            if (
                not self.instance.pk
                and inscriptions_actives.count() >= session.capacite_max
            ):
                self.add_error(
                    "session",
                    "Cette session a atteint sa capacité maximale.",
                )
        return cleaned_data

    def save(self, commit=True):
        inscription = super().save(commit=False)
        inscription.prix_initial = inscription.session.prix_applique
        inscription.montant_final = (
            inscription.prix_initial - (inscription.remise or Decimal("0"))
        )
        if commit:
            inscription.save()
        return inscription


class NouvelApprenantInscriptionForm(forms.Form):
    prenom = forms.CharField(label="Prénom", max_length=150)
    nom = forms.CharField(label="Nom", max_length=150)
    telephone = forms.CharField(label="Téléphone", max_length=30)
    email = forms.EmailField(label="Email", required=False)
    genre = forms.ChoiceField(label="Genre", choices=Participant.Genre.choices)
    date_naissance = forms.DateField(
        label="Date de naissance",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    ville = forms.CharField(label="Ville", max_length=150, required=False)
    profession = forms.CharField(label="Profession", max_length=150, required=False)
    entreprise = forms.CharField(label="Entreprise", max_length=255, required=False)
    session = forms.ModelChoiceField(
        label="Session de formation",
        queryset=SessionFormation.objects.none(),
    )
    date_inscription = forms.DateField(
        label="Date d’inscription",
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    remise = forms.DecimalField(
        label="Remise (FCFA)",
        max_digits=12,
        decimal_places=2,
        min_value=0,
        initial=0,
    )
    statut = forms.ChoiceField(
        label="Statut de l’inscription",
        choices=Inscription.Statut.choices,
        initial=Inscription.Statut.PREINSCRIT,
    )
    observations = forms.CharField(
        label="Observations",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        organisation = kwargs.pop("organisation", None)
        super().__init__(*args, **kwargs)
        sessions = SessionFormation.objects.exclude(
            statut__in=[
                SessionFormation.Statut.ANNULEE,
                SessionFormation.Statut.TERMINEE,
            ]
        ).select_related("formation")
        if organisation:
            sessions = sessions.filter(organisation=organisation)
        self.fields["session"].queryset = sessions.order_by("-date_debut")
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full rounded-md border border-slate-300 bg-white px-3.5 py-3 "
                "text-sm outline-none focus:border-blue-600 focus:ring-2 "
                "focus:ring-blue-100"
            )

    def clean(self):
        cleaned_data = super().clean()
        session = cleaned_data.get("session")
        remise = cleaned_data.get("remise") or Decimal("0")
        if session:
            if remise > session.prix_applique:
                self.add_error(
                    "remise",
                    "La remise ne peut pas dépasser le prix de la session.",
                )
            if (
                session.inscriptions.exclude(
                    statut=Inscription.Statut.ANNULE
                ).count()
                >= session.capacite_max
            ):
                self.add_error(
                    "session",
                    "Cette session a atteint sa capacité maximale.",
                )
        return cleaned_data
