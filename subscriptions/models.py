from datetime import timedelta
from math import ceil

from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel


class PlanAbonnement(TimeStampedModel):
    class Code(models.TextChoices):
        STARTER = "STARTER", "Basic"
        PREMIUM = "PREMIUM", "Business"
        PRO = "PRO", "Enterprise"

    code = models.CharField(max_length=20, choices=Code.choices, unique=True)
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    prix_mensuel = models.DecimalField(max_digits=12, decimal_places=2)
    prix_annuel = models.DecimalField(max_digits=12, decimal_places=2)
    max_utilisateurs = models.PositiveIntegerField()
    max_participants = models.PositiveIntegerField()
    max_formations_actives = models.PositiveIntegerField()
    max_stockage_mo = models.PositiveIntegerField()
    fonctionnalites = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["ordre", "prix_mensuel"]
        verbose_name = "Plan d'abonnement"
        verbose_name_plural = "Plans d'abonnement"

    def __str__(self):
        return self.nom


class Abonnement(TimeStampedModel):
    class Statut(models.TextChoices):
        ESSAI = "ESSAI", "Essai"
        ACTIF = "ACTIF", "Actif"
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        EXPIRE = "EXPIRE", "Expire"
        SUSPENDU = "SUSPENDU", "Suspendu"
        ANNULE = "ANNULE", "Annule"

    class Cycle(models.TextChoices):
        MENSUEL = "MENSUEL", "Mensuel"
        ANNUEL = "ANNUEL", "Annuel"

    organisation = models.OneToOneField(
        "organisations.Organisation",
        on_delete=models.CASCADE,
        related_name="abonnement",
    )
    plan = models.ForeignKey(
        PlanAbonnement,
        on_delete=models.PROTECT,
        related_name="abonnements",
    )
    cycle = models.CharField(
        max_length=20,
        choices=Cycle.choices,
        default=Cycle.MENSUEL,
    )
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.ESSAI,
        db_index=True,
    )
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    renouvellement_automatique = models.BooleanField(default=False)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    jours_grace = models.PositiveIntegerField(default=3)

    class Meta:
        ordering = ["-date_fin"]
        verbose_name = "Abonnement"
        verbose_name_plural = "Abonnements"

    def __str__(self):
        return f"{self.organisation} - {self.plan} ({self.get_statut_display()})"

    @property
    def is_active(self):
        return self.statut in {self.Statut.ACTIF, self.Statut.ESSAI}

    @property
    def is_expired(self):
        return self.date_fin < timezone.now()

    @property
    def grace_ends_at(self):
        return self.date_fin + timedelta(days=self.jours_grace)

    @property
    def is_in_grace_period(self):
        now = timezone.now()
        return self.date_fin < now <= self.grace_ends_at

    @property
    def is_read_only(self):
        return self.is_expired and not self.is_in_grace_period

    @property
    def days_remaining(self):
        return ceil((self.date_fin - timezone.now()).total_seconds() / 86400)


class PaiementAbonnement(TimeStampedModel):
    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        VALIDE = "VALIDE", "Valide"
        ECHOUE = "ECHOUE", "Echoue"
        ANNULE = "ANNULE", "Annule"
        REMBOURSE = "REMBOURSE", "Rembourse"

    abonnement = models.ForeignKey(
        Abonnement,
        on_delete=models.PROTECT,
        related_name="paiements",
    )
    reference = models.CharField(max_length=100, unique=True)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    mode_paiement = models.CharField(max_length=50)
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE,
        db_index=True,
    )
    date_paiement = models.DateTimeField(null=True, blank=True)
    donnees_prestataire = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Paiement d'abonnement"
        verbose_name_plural = "Paiements d'abonnement"

    def __str__(self):
        return f"{self.reference} - {self.montant}"
