from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from organisations.utils import require_request_organisation

from .models import CompteComptable, EcritureComptable, LigneEcritureComptable


class EcritureForm(forms.ModelForm):
    class Meta:
        model = EcritureComptable
        fields = ["journal", "exercice", "date_ecriture", "reference", "libelle", "piece"]
        widgets = {"date_ecriture": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, organisation=None, **kwargs):
        super().__init__(*args, **kwargs)
        if organisation is not None:
            self.fields["exercice"].queryset = self.fields[
                "exercice"
            ].queryset.filter(organisation=organisation)

    def clean(self):
        cleaned = super().clean()
        exercice = cleaned.get("exercice")
        date_ecriture = cleaned.get("date_ecriture")
        journal = cleaned.get("journal")
        if exercice and exercice.cloture:
            self.add_error("exercice", "Cet exercice est cloture.")
        if exercice and date_ecriture and not exercice.date_debut <= date_ecriture <= exercice.date_fin:
            self.add_error("date_ecriture", "Cette date est hors de l'exercice selectionne.")
        if journal and not journal.actif:
            self.add_error("journal", "Ce journal est inactif.")
        return cleaned


class BaseLigneFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        count = 0
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            compte = form.cleaned_data.get("compte")
            debit = form.cleaned_data.get("debit") or Decimal("0")
            credit = form.cleaned_data.get("credit") or Decimal("0")
            if not compte and not debit and not credit:
                continue
            count += 1
            if compte and (not compte.actif or not compte.est_mouvement):
                raise ValidationError("Toutes les lignes doivent utiliser un compte actif mouvementable.")
            if (debit > 0) == (credit > 0):
                raise ValidationError("Chaque ligne doit avoir soit un debit, soit un credit.")
            total_debit += debit
            total_credit += credit
        if count < 2:
            raise ValidationError("Ajoutez au moins deux lignes comptables.")
        if total_debit <= 0 or total_debit != total_credit:
            raise ValidationError(
                f"L'ecriture doit etre equilibree : debit {total_debit} / credit {total_credit}."
            )


LigneEcritureFormSet = inlineformset_factory(
    EcritureComptable,
    LigneEcritureComptable,
    formset=BaseLigneFormSet,
    fields=["compte", "libelle", "debit", "credit"],
    extra=4,
    can_delete=True,
    min_num=2,
    validate_min=True,
)


class CompteComptableForm(forms.ModelForm):
    class Meta:
        model = CompteComptable
        fields = [
            "code",
            "libelle",
            "parent",
            "nature",
            "sens",
            "niveau",
            "type_compte",
            "est_mouvement",
            "categorie",
            "actif",
        ]

    def __init__(self, *args, organisation, **kwargs):
        super().__init__(*args, **kwargs)
        self.organisation = organisation
        self.fields["parent"].queryset = CompteComptable.objects.filter(
            organisation=organisation
        ).exclude(pk=self.instance.pk).order_by("code")
        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm",
            )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        doublon = CompteComptable.objects.filter(
            organisation=self.organisation, code=code
        ).exclude(pk=self.instance.pk)
        if doublon.exists():
            raise forms.ValidationError("Ce numéro de compte existe déjà.")
        return code


class RequestOrganisationFormMixin:
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["organisation"] = require_request_organisation(self.request)
        return kwargs
