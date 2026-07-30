from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from core.models import OrganisationOwnedModel


class EcritureComptable(OrganisationOwnedModel, models.Model):
    """Écriture comptable en partie double."""

    reference = models.CharField(_("Référence"), max_length=50, unique=True)
    date_ecriture = models.DateField(_("Date d'écriture"))
    libelle = models.TextField(_("Libellé"))
    journal = models.ForeignKey(
        "JournalComptable",
        on_delete=models.CASCADE,
        verbose_name=_("Journal"),
    )
    piece = models.CharField(
        _("Pièce"), max_length=50, blank=True, null=True
    )
    exercice = models.ForeignKey(
        "ExerciceComptable",
        on_delete=models.CASCADE,
        verbose_name=_("Exercice"),
    )
    validee = models.BooleanField(_("Validée"), default=False)
    date_validation = models.DateTimeField(
        _("Date validation"), null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(
        _("Créé par"), max_length=100, blank=True, null=True
    )

    class Meta:
        verbose_name = _("Écriture comptable")
        verbose_name_plural = _("Écritures comptables")
        ordering = ["-date_ecriture", "-created_at"]
        indexes = [
            models.Index(fields=["reference"]),
            models.Index(fields=["date_ecriture"]),
            models.Index(fields=["journal", "date_ecriture"]),
        ]

    def __str__(self):
        return f"{self.reference} - {self.date_ecriture} - {self.libelle[:60]}"

    def clean(self):
        super().clean()
        if self.exercice_id:
            if self.exercice.cloture:
                raise ValidationError("L'exercice comptable est clôturé.")
            if not (
                self.exercice.date_debut
                <= self.date_ecriture
                <= self.exercice.date_fin
            ):
                raise ValidationError(
                    "La date de l'écriture est hors de l'exercice sélectionné."
                )

    @property
    def total_debit(self):
        return (
            self.lignes.aggregate(total=models.Sum("debit"))["total"]
            or Decimal("0.00")
        )

    @property
    def total_credit(self):
        return (
            self.lignes.aggregate(total=models.Sum("credit"))["total"]
            or Decimal("0.00")
        )

    @property
    def est_equilibree(self):
        return self.total_debit > 0 and self.total_debit == self.total_credit


class LigneEcritureComptable(models.Model):
    """Ligne d'une écriture comptable."""

    ecriture = models.ForeignKey(
        EcritureComptable,
        on_delete=models.CASCADE,
        related_name="lignes",
        verbose_name=_("Écriture"),
    )
    compte = models.ForeignKey(
        "CompteComptable",
        on_delete=models.PROTECT,
        verbose_name=_("Compte"),
    )
    debit = models.DecimalField(
        _("Débit"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    credit = models.DecimalField(
        _("Crédit"),
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    libelle = models.CharField(
        _("Libellé ligne"), max_length=200, blank=True, null=True
    )

    class Meta:
        verbose_name = _("Ligne d'écriture")
        verbose_name_plural = _("Lignes d'écritures")
        indexes = [models.Index(fields=["compte"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(debit__gte=0) & Q(credit__gte=0),
                name="ligne_montants_positifs",
            ),
            models.CheckConstraint(
                condition=(
                    Q(debit__gt=0, credit=0)
                    | Q(credit__gt=0, debit=0)
                ),
                name="ligne_un_seul_sens",
            ),
        ]

    def __str__(self):
        return (
            f"{self.ecriture.reference} - {self.compte.code} - "
            f"{self.debit or self.credit:,.0f}"
        )

    def clean(self):
        super().clean()
        if self.debit and self.credit:
            raise ValidationError(
                _("Une ligne ne peut pas avoir débit ET crédit.")
            )
        if not self.debit and not self.credit:
            raise ValidationError(
                _("Une ligne doit avoir un débit ou un crédit.")
            )
        if self.debit < 0 or self.credit < 0:
            raise ValidationError(_("Les montants doivent être positifs."))
        if self.compte_id and not self.compte.est_mouvement:
            raise ValidationError(
                _("Le compte sélectionné n'accepte pas de mouvements.")
            )
