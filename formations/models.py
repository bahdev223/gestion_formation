from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from uuid import uuid4

from core.models import TimeStampedModel


class CategorieFormation(TimeStampedModel):
    nom = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    couleur = models.CharField(max_length=20, default="#2563EB")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.nom


class Formation(TimeStampedModel):
    class UniteDuree(models.TextChoices):
        HEURES = "HEURES", "Heures"
        JOURS = "JOURS", "Jours"
        SEMAINES = "SEMAINES", "Semaines"

    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", "Brouillon"
        ACTIVE = "ACTIVE", "Active"
        ARCHIVEE = "ARCHIVEE", "Archivee"

    code = models.CharField(max_length=30, unique=True, editable=False)
    nom = models.CharField(max_length=255)
    categorie = models.ForeignKey(CategorieFormation, on_delete=models.PROTECT, related_name="formations")
    description = models.TextField(blank=True)
    objectifs = models.TextField(blank=True)
    programme = models.TextField(blank=True)
    duree = models.PositiveIntegerField()
    unite_duree = models.CharField(max_length=20, choices=UniteDuree.choices, default=UniteDuree.HEURES)
    prix_standard = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to="formations/images/", null=True, blank=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.BROUILLON)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"FOR-{timezone.localdate():%Y%m%d}-{uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.nom}" if self.code else self.nom


class SessionFormation(TimeStampedModel):
    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", "Brouillon"
        PLANIFIEE = "PLANIFIEE", "Planifiee"
        INSCRIPTIONS_OUVERTES = "INSCRIPTIONS_OUVERTES", "Inscriptions ouvertes"
        COMPLETE = "COMPLETE", "Complete"
        EN_COURS = "EN_COURS", "En cours"
        TERMINEE = "TERMINEE", "Terminee"
        ANNULEE = "ANNULEE", "Annulee"

    code = models.CharField(max_length=30, unique=True, editable=False)
    formation = models.ForeignKey(Formation, on_delete=models.PROTECT, related_name="sessions")
    titre = models.CharField(max_length=255)
    formateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sessions_formateur")
    date_debut = models.DateField()
    date_fin = models.DateField()
    heure_debut = models.TimeField(null=True, blank=True)
    heure_fin = models.TimeField(null=True, blank=True)
    lieu = models.CharField(max_length=255)
    capacite_max = models.PositiveIntegerField(default=20)
    prix_applique = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    seuil_presence_attestation = models.DecimalField(max_digits=5, decimal_places=2, default=75)
    paiement_requis_attestation = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    statut = models.CharField(max_length=30, choices=Statut.choices, default=Statut.BROUILLON)

    def __str__(self):
        return f"{self.titre} — {self.formation.nom}"


class Seance(TimeStampedModel):
    class Statut(models.TextChoices):
        PLANIFIEE = "PLANIFIEE", "Planifiee"
        EN_COURS = "EN_COURS", "En cours"
        TERMINEE = "TERMINEE", "Terminee"
        ANNULEE = "ANNULEE", "Annulee"

    session = models.ForeignKey(SessionFormation, on_delete=models.CASCADE, related_name="seances")
    titre = models.CharField(max_length=255)
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    lieu = models.CharField(max_length=255, blank=True)
    contenu = models.TextField(blank=True)
    observations = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.PLANIFIEE)

    class Meta:
        ordering = ["date", "heure_debut"]
        constraints = [
            models.UniqueConstraint(fields=["session", "date", "heure_debut"], name="unique_seance_session_date_heure")
        ]
