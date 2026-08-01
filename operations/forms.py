"""Formulaires d'operation.

Le formulaire se construit a partir du catalogue : chaque type declare les
champs dont il a besoin, et seuls ceux-la sont presentes. L'utilisateur ne voit
donc jamais un debit, un credit ni un numero de compte comptable.
"""

import copy

from django import forms
from django.utils.translation import gettext_lazy as _

from comptes.models import Compte
from core.features import module_est_actif

from .catalogue import choix_types, choix_types_simples, obtenir
from .models import Operation

CLASSES_CHAMP = (
    "w-full rounded-lg border border-[var(--fx-border)] bg-white px-3.5 py-2.5 "
    "text-[15px] outline-none transition focus:border-[var(--fx-primary)]"
)

# Definition des champs supplementaires que le catalogue peut demander.
CHAMPS_SUPPLEMENTAIRES = {
    "tiers": forms.CharField(
        label=_("Tiers"), max_length=150, required=False,
        help_text=_("Client, fournisseur ou bénéficiaire concerné."),
    ),
    "beneficiaire": forms.CharField(
        label=_("Bénéficiaire"), max_length=150, required=False,
    ),
    "motif": forms.CharField(label=_("Motif"), max_length=255, required=False),
    "numero_piece": forms.CharField(
        label=_("Numéro de pièce"), max_length=60, required=False,
    ),
    "reference_externe": forms.CharField(
        label=_("Référence"), max_length=60, required=False,
        help_text=_("Numéro de reçu, de transaction mobile money…"),
    ),
    "periode_concernee": forms.CharField(
        label=_("Période concernée"), max_length=40, required=False,
        help_text=_("Par exemple : 07/2026."),
    ),
    "date_echeance": forms.DateField(
        label=_("Date d'échéance"), required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    ),
    "montant_tva": forms.DecimalField(
        label=_("Dont TVA"), required=False, min_value=0,
        max_digits=14, decimal_places=2,
    ),
}

# Ces champs existent sur le modele : ils ne passent pas par « donnees ».
CHAMPS_MODELE = {"compte_tresorerie", "compte_destination", "centre_cout", "projet"}


class OperationForm(forms.ModelForm):
    """Socle commun, complete dynamiquement selon le type choisi."""

    type_operation = forms.ChoiceField(
        label=_("Type d'opération"), choices=(), required=True
    )

    class Meta:
        model = Operation
        fields = [
            "type_operation",
            "date_operation",
            "description",
            "montant",
            "compte_tresorerie",
            "compte_destination",
            "centre_cout",
            "projet",
            "justificatif",
        ]
        widgets = {
            "date_operation": forms.DateInput(attrs={"type": "date"}),
            "description": forms.TextInput(),
        }
        labels = {
            "date_operation": _("Date"),
            "description": _("Description"),
            "montant": _("Montant"),
        }

    def __init__(self, *args, organisation=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organisation = organisation
        if organisation is not None:
            self.fields["montant"].label = _("Montant (%(devise)s)") % {
                "devise": organisation.devise
            }
        self.fields["montant"].widget.attrs.update(
            {"inputmode": "decimal", "min": "0.01", "step": "0.01"}
        )
        afficher_comptabilite = organisation is not None and module_est_actif(
            organisation, "comptabilite"
        )
        groupes = choix_types() if afficher_comptabilite else choix_types_simples()
        self.fields["type_operation"].choices = [("", "— Choisir —")] + list(groupes)
        # Le widget Django rend deja les groupes : on lui attache seulement le
        # rechargement, plutot que de reconstruire le <select> en template.
        self.fields["type_operation"].widget.attrs["onchange"] = (
            "rechargerFormulaire(this.value)"
        )

        # Les comptes proposes sont ceux de l'organisation, jamais d'une autre.
        comptes = Compte.objects.none()
        if organisation is not None:
            comptes = Compte.objects.filter(
                organisation=organisation, actif=True
            ).order_by("nom")
        for nom in ("compte_tresorerie", "compte_destination"):
            self.fields[nom].queryset = comptes
            self.fields[nom].required = False

        self.definition = obtenir(self._type_choisi())
        self._ajouter_champs_du_type()
        self._masquer_champs_inutiles()
        self._styler()

    def _type_choisi(self):
        if self.data.get("type_operation"):
            return self.data.get("type_operation")
        if self.initial.get("type_operation"):
            return self.initial["type_operation"]
        return getattr(self.instance, "type_operation", "") or ""

    def _ajouter_champs_du_type(self):
        if self.definition is None:
            return
        valeurs = getattr(self.instance, "donnees", None) or {}
        for nom in self.definition.champs:
            if nom in CHAMPS_MODELE:
                continue
            gabarit = CHAMPS_SUPPLEMENTAIRES.get(nom)
            if gabarit is None:
                continue
            # Copie : les gabarits sont partages entre toutes les instances de
            # formulaire, il ne faut pas leur poser une valeur initiale.
            champ = copy.deepcopy(gabarit)
            champ.initial = valeurs.get(nom)
            self.fields[nom] = champ

    def _masquer_champs_inutiles(self):
        """Retire les champs modele que ce type n'utilise pas."""
        if self.definition is None:
            # Tant qu'aucun type n'est choisi, on ne demande que le socle.
            for nom in CHAMPS_MODELE:
                self.fields.pop(nom, None)
            return
        attendus = set(self.definition.champs)
        for nom in CHAMPS_MODELE:
            if nom not in attendus:
                self.fields.pop(nom, None)
        if self.definition.exige_compte_tresorerie and "compte_tresorerie" in self.fields:
            self.fields["compte_tresorerie"].required = True

    def _styler(self):
        for champ in self.fields.values():
            if isinstance(champ.widget, forms.CheckboxInput):
                continue
            champ.widget.attrs.setdefault("class", CLASSES_CHAMP)

    def clean_montant(self):
        montant = self.cleaned_data.get("montant")
        if montant is not None and montant <= 0:
            raise forms.ValidationError(_("Le montant doit être positif."))
        return montant

    def clean(self):
        donnees = super().clean()
        definition = obtenir(donnees.get("type_operation"))
        if definition is None:
            self.add_error("type_operation", _("Type d'opération inconnu."))
            return donnees

        if definition.exige_compte_tresorerie and not donnees.get("compte_tresorerie"):
            self.add_error(
                "compte_tresorerie",
                _("Cette opération nécessite un compte de trésorerie."),
            )
        if definition.code in {"TRANSFERT", "DEPOT_BANQUE", "RETRAIT_BANQUE"}:
            source = donnees.get("compte_tresorerie")
            destination = donnees.get("compte_destination")
            if not destination:
                self.add_error(
                    "compte_destination", _("Indiquez le compte de destination.")
                )
            elif source and destination.pk == source.pk:
                self.add_error(
                    "compte_destination",
                    _("Le compte de destination doit différer de la source."),
                )
        return donnees

    def save(self, commit=True):
        operation = super().save(commit=False)
        if self.organisation is not None:
            operation.organisation = self.organisation

        # Les champs propres au type sont regroupes dans « donnees » : ajouter
        # un type ne demande donc aucune migration.
        supplementaires = {}
        if self.definition is not None:
            for nom in self.definition.champs:
                if nom in CHAMPS_MODELE or nom not in self.cleaned_data:
                    continue
                valeur = self.cleaned_data.get(nom)
                if valeur in (None, ""):
                    continue
                supplementaires[nom] = str(valeur)
        operation.donnees = supplementaires

        if commit:
            operation.save()
        return operation
