from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from uuid import uuid4

from core.models import TimeStampedModel


class Inscription(TimeStampedModel):
    class Statut(models.TextChoices):
        PREINSCRIT = "PREINSCRIT", "Preinscrit"
        CONFIRME = "CONFIRME", "Confirme"
        EN_COURS = "EN_COURS", "En cours"
        TERMINE = "TERMINE", "Termine"
        ABANDONNE = "ABANDONNE", "Abandonne"
        ANNULE = "ANNULE", "Annule"

    class StatutPaiement(models.TextChoices):
        NON_PAYE = "NON_PAYE", "Non paye"
        PARTIEL = "PARTIEL", "Partiellement paye"
        PAYE = "PAYE", "Paye"
        TROP_PERCU = "TROP_PERCU", "Trop-percu"
        REMBOURSE = "REMBOURSE", "Rembourse"

    numero = models.CharField(max_length=30, unique=True, editable=False)
    participant = models.ForeignKey("participants.Participant", on_delete=models.PROTECT, related_name="inscriptions")
    session = models.ForeignKey("formations.SessionFormation", on_delete=models.PROTECT, related_name="inscriptions")
    date_inscription = models.DateField(default=timezone.localdate)
    prix_initial = models.DecimalField(max_digits=12, decimal_places=2)
    remise = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_final = models.DecimalField(max_digits=12, decimal_places=2)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.PREINSCRIT)
    statut_paiement = models.CharField(max_length=20, choices=StatutPaiement.choices, default=StatutPaiement.NON_PAYE)
    entreprise_payeur = models.CharField(max_length=255, blank=True)
    reference_externe = models.CharField(max_length=100, blank=True)
    observations = models.TextField(blank=True)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inscriptions_creees")
    annulee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="inscriptions_annulees")
    date_annulation = models.DateTimeField(null=True, blank=True)
    motif_annulation = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = (
                f"INS-{timezone.localdate():%Y%m%d}-{uuid4().hex[:6].upper()}"
            )
        if self.montant_final is None:
            self.montant_final = self.prix_initial - self.remise
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero} - {self.participant.nom_complet}"

    @property
    def total_paye(self):
        return self.paiements.filter(statut="VALIDE").aggregate(total=Sum("montant"))["total"] or Decimal("0")

    @property
    def reste_a_payer(self):
        return max(self.montant_final - self.total_paye, Decimal("0"))


class HistoriqueStatutInscription(TimeStampedModel):
    inscription = models.ForeignKey(Inscription, on_delete=models.CASCADE, related_name="historique_statuts")
    ancien_statut = models.CharField(max_length=20)
    nouveau_statut = models.CharField(max_length=20)
    commentaire = models.TextField(blank=True)
    modifie_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
