from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from core.models import TimeStampedModel


class Organisation(TimeStampedModel):
    class Statut(models.TextChoices):
        ESSAI = "ESSAI", "Periode d'essai"
        ACTIVE = "ACTIVE", "Active"
        SUSPENDUE = "SUSPENDUE", "Suspendue"
        EXPIREE = "EXPIREE", "Abonnement expire"
        FERMEE = "FERMEE", "Fermee"

    nom = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    logo = models.ImageField(upload_to="organisations/logos/", null=True, blank=True)
    email = models.EmailField()
    telephone = models.CharField(max_length=30)
    adresse = models.TextField(blank=True)
    ville = models.CharField(max_length=150, blank=True)
    pays = models.CharField(max_length=100, default="Mali")
    devise = models.CharField(max_length=10, default="FCFA")
    fuseau_horaire = models.CharField(max_length=100, default="Africa/Bamako")
    statut = models.CharField(
        max_length=20,
        choices=Statut.choices,
        default=Statut.ESSAI,
        db_index=True,
    )
    date_fin_essai = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["nom"]
        verbose_name = "Organisation"
        verbose_name_plural = "Organisations"

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        if self.statut == self.Statut.ESSAI and not self.date_fin_essai:
            self.date_fin_essai = timezone.now() + timedelta(days=14)
        super().save(*args, **kwargs)

    @property
    def is_trial_active(self):
        return (
            self.statut == self.Statut.ESSAI
            and self.date_fin_essai
            and self.date_fin_essai >= timezone.now()
        )

    @property
    def can_access(self):
        return self.is_active and self.statut not in {
            self.Statut.SUSPENDUE,
            self.Statut.FERMEE,
        }


class MembreOrganisation(TimeStampedModel):
    class Role(models.TextChoices):
        PROPRIETAIRE = "PROPRIETAIRE", "Proprietaire"
        ADMIN = "ADMIN", "Administrateur"
        RESPONSABLE = "RESPONSABLE", "Responsable formation"
        FORMATEUR = "FORMATEUR", "Formateur"
        COMPTABLE = "COMPTABLE", "Comptable"
        LECTURE = "LECTURE", "Lecture seule"

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="membres",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organisations",
    )
    role = models.CharField(max_length=30, choices=Role.choices)
    is_active = models.BooleanField(default=True, db_index=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitations_organisations",
    )

    class Meta:
        ordering = ["organisation__nom", "user__username"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "user"],
                name="unique_user_organisation",
            )
        ]
        verbose_name = "Membre d'organisation"
        verbose_name_plural = "Membres d'organisation"

    def __str__(self):
        return f"{self.user} - {self.organisation} ({self.get_role_display()})"

    @property
    def is_owner(self):
        return self.role == self.Role.PROPRIETAIRE
