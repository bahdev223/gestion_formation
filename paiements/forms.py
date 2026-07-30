from decimal import Decimal

from django import forms

from inscriptions.models import Inscription

from .models import Paiement


class PaiementForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = [
            "inscription",
            "montant",
            "date_paiement",
            "mode_paiement",
            "reference_transaction",
            "payeur_nom",
            "observations",
        ]
        labels = {
            "inscription": "Inscription concernée",
            "montant": "Montant encaissé (FCFA)",
            "date_paiement": "Date et heure du paiement",
            "mode_paiement": "Mode de paiement",
            "reference_transaction": "Référence de transaction",
            "payeur_nom": "Nom du payeur",
        }
        widgets = {
            "montant": forms.NumberInput(attrs={"min": 1, "step": 500}),
            "date_paiement": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "observations": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        organisation = kwargs.pop("organisation", None)
        super().__init__(*args, **kwargs)
        self.fields["date_paiement"].input_formats = ["%Y-%m-%dT%H:%M"]
        inscriptions = Inscription.objects.exclude(
            statut=Inscription.Statut.ANNULE
        ).exclude(
            statut_paiement=Inscription.StatutPaiement.PAYE
        ).select_related(
            "participant", "session", "session__formation"
        )
        if organisation:
            inscriptions = inscriptions.filter(organisation=organisation)
        self.fields["inscription"].queryset = inscriptions.order_by("-date_inscription")
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full rounded-md border border-slate-300 bg-white px-3.5 py-3 "
                "text-sm outline-none focus:border-blue-600 focus:ring-2 "
                "focus:ring-blue-100"
            )

    def clean(self):
        cleaned_data = super().clean()
        inscription = cleaned_data.get("inscription")
        amount = cleaned_data.get("montant") or Decimal("0")
        if inscription and amount > inscription.reste_a_payer:
            self.add_error(
                "montant",
                f"Le montant dépasse le reste à payer "
                f"({inscription.reste_a_payer:,.0f} FCFA).",
            )
        return cleaned_data
