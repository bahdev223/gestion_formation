from decimal import Decimal

from django import forms

from comptes.models import Compte
from comptes.models.compte import TypeCompte
from inscriptions.models import Inscription

from .models import Paiement


class MoneyDecimalField(forms.DecimalField):
    def to_python(self, value):
        if isinstance(value, str):
            normalized = (
                value.strip()
                .replace("\u00a0", "")
                .replace(" ", "")
                .replace("FCFA", "")
                .replace("XOF", "")
                .replace("EUR", "")
                .replace("USD", "")
                .replace("€", "")
                .replace("$", "")
            )
            if "," in normalized and "." in normalized:
                normalized = normalized.replace(".", "").replace(",", ".")
            elif "," in normalized:
                normalized = normalized.replace(",", ".")
            elif normalized.count(".") > 1:
                normalized = normalized.replace(".", "")
            value = normalized
        return super().to_python(value)


class PaiementForm(forms.ModelForm):
    ACCOUNT_TYPE_TO_MODE = {
        TypeCompte.ESPECES: Paiement.ModePaiement.ESPECES,
        TypeCompte.MOBILE_MONEY: Paiement.ModePaiement.MOBILE_MONEY,
        TypeCompte.PORTEFEUILLE_NUMERIQUE: Paiement.ModePaiement.MOBILE_MONEY,
        TypeCompte.BANQUE: Paiement.ModePaiement.BANQUE,
        TypeCompte.CARTE: Paiement.ModePaiement.CARTE,
        TypeCompte.AUTRE: Paiement.ModePaiement.AUTRE,
    }

    montant = MoneyDecimalField(
        label="Montant encaissé",
        min_value=Decimal("1"),
        max_digits=12,
        decimal_places=2,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "inputmode": "decimal",
                "placeholder": "Ex : 1 500",
                "x-on:input": "$el.value = $el.value.replace(/[^0-9.,\\s]/g, '')",
            }
        ),
    )

    class Meta:
        model = Paiement
        fields = [
            "inscription",
            "compte",
            "mode_paiement",
            "montant",
            "date_paiement",
            "reference_transaction",
            "payeur_nom",
            "observations",
        ]
        labels = {
            "inscription": "Inscription concernée",
            "date_paiement": "Date et heure du paiement",
            "mode_paiement": "Mode de paiement",
            "compte": "Compte d'encaissement",
            "reference_transaction": "Référence de transaction",
            "payeur_nom": "Nom du payeur",
            "observations": "Observations",
        }
        widgets = {
            "date_paiement": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "observations": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        organisation = kwargs.pop("organisation", None)
        super().__init__(*args, **kwargs)
        self.organisation = organisation
        self.devise = getattr(organisation, "devise", None) or "Devise"
        self.fields["date_paiement"].input_formats = ["%Y-%m-%dT%H:%M"]
        self.fields["montant"].label = f"Montant encaissé ({self.devise})"

        inscriptions = (
            Inscription.objects.exclude(statut=Inscription.Statut.ANNULE)
            .exclude(statut_paiement=Inscription.StatutPaiement.PAYE)
            .select_related("participant", "session", "session__formation")
        )
        comptes = Compte.objects.filter(actif=True)
        if organisation:
            inscriptions = inscriptions.filter(organisation=organisation)
            comptes = comptes.filter(organisation=organisation)

        self.fields["inscription"].queryset = inscriptions.order_by("-date_inscription")
        self.fields["inscription"].widget.attrs["x-model"] = "selectedInscription"
        self.fields["compte"].queryset = comptes.order_by("type", "code", "nom")
        self.fields["compte"].required = True
        self.fields["compte"].empty_label = "Choisir la caisse ou le compte"
        self.fields["compte"].widget.attrs.update(
            {
                "x-model": "selectedAccount",
                "x-on:change": "selectedMode = accountModeMap[selectedAccount] || ''",
            }
        )
        self.fields["mode_paiement"].widget.attrs.update(
            {
                "x-model": "selectedMode",
                "x-bind:disabled": "!selectedAccount",
            }
        )
        self.fields["mode_paiement"].help_text = (
            "Le mode est aligné automatiquement avec le type du compte choisi."
        )

        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "w-full rounded-md border border-slate-300 bg-white px-3.5 py-3 "
                "text-sm outline-none focus:border-blue-600 focus:ring-2 "
                "focus:ring-blue-100"
            )
        self.fields["montant"].widget.attrs["class"] += " pr-16 font-semibold"

    def clean(self):
        cleaned_data = super().clean()
        inscription = cleaned_data.get("inscription")
        compte = cleaned_data.get("compte")
        mode_paiement = cleaned_data.get("mode_paiement")
        amount = cleaned_data.get("montant") or Decimal("0")
        if inscription and amount > inscription.reste_a_payer:
            self.add_error(
                "montant",
                f"Le montant dépasse le reste à payer "
                f"({inscription.reste_a_payer:,.0f} {self.devise}).",
            )
        if compte and mode_paiement:
            expected_mode = self.ACCOUNT_TYPE_TO_MODE.get(compte.type)
            if expected_mode and mode_paiement != expected_mode:
                self.add_error(
                    "mode_paiement",
                    (
                        "Le mode ne correspond pas au compte choisi. "
                        f"Pour {compte.nom}, utilisez "
                        f"{Paiement.ModePaiement(expected_mode).label}."
                    ),
                )
        return cleaned_data
