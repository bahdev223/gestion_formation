from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrateur"
        RESPONSABLE = "RESPONSABLE", "Responsable formation"
        FORMATEUR = "FORMATEUR", "Formateur"
        COMPTABLE = "COMPTABLE", "Comptable"
        RH = "RH", "Responsable RH"
        CAISSIER = "CAISSIER", "Caissier"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RESPONSABLE)
    telephone = models.CharField(max_length=30, blank=True)
    photo = models.ImageField(upload_to="users/photos/", null=True, blank=True)
    must_change_password = models.BooleanField(default=False)
    salaire_mensuel = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        help_text="Salaire mensuel utilisé par le module de paie simple.",
    )


class FormateurProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="formateur_profile")
    specialite = models.CharField(max_length=255, blank=True)
    biographie = models.TextField(blank=True)
    tarif_horaire = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    disponibilite_notes = models.TextField(blank=True)
