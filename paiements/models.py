from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import OrganisationOwnedModel, TimeStampedModel


class Paiement(OrganisationOwnedModel, TimeStampedModel):
    class ModePaiement(models.TextChoices):
        ESPECES = "ESPECES", "Especes"
        ORANGE_MONEY = "ORANGE_MONEY", "Orange Money"
        MOOV_MONEY = "MOOV_MONEY", "Moov Money"
        VIREMENT = "VIREMENT", "Virement bancaire"
        CHEQUE = "CHEQUE", "Cheque"
        AUTRE = "AUTRE", "Autre"

    class Statut(models.TextChoices):
        VALIDE = "VALIDE", "Valide"
        ANNULE = "ANNULE", "Annule"
        REMBOURSE = "REMBOURSE", "Rembourse"

    numero = models.CharField(max_length=30, unique=True, editable=False)
    numero_recu = models.CharField(max_length=30, unique=True, editable=False)
    inscription = models.ForeignKey("inscriptions.Inscription", on_delete=models.PROTECT, related_name="paiements")
    montant = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("1"))])
    date_paiement = models.DateTimeField(default=timezone.now)
    mode_paiement = models.CharField(max_length=30, choices=ModePaiement.choices)
    reference_transaction = models.CharField(max_length=150, blank=True)
    payeur_nom = models.CharField(max_length=255, blank=True)
    observations = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.VALIDE)
    enregistre_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="paiements_enregistres")
    annule_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="paiements_annules")
    date_annulation = models.DateTimeField(null=True, blank=True)
    motif_annulation = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        token = uuid4().hex[:7].upper()
        date_code = timezone.localdate().strftime("%Y%m%d")
        if not self.numero:
            self.numero = f"PAY-{date_code}-{token}"
        if not self.numero_recu:
            self.numero_recu = f"REC-{date_code}-{token}"
        super().save(*args, **kwargs)


class Remboursement(OrganisationOwnedModel, TimeStampedModel):
    paiement = models.ForeignKey(Paiement, on_delete=models.PROTECT, related_name="remboursements")
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date_remboursement = models.DateTimeField(default=timezone.now)
    motif = models.TextField()
    mode_remboursement = models.CharField(max_length=30, choices=Paiement.ModePaiement.choices)
    reference = models.CharField(max_length=150, blank=True)
    effectue_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
