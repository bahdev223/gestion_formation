from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from uuid import uuid4

from core.constants import GENRE_CHOICES
from core.models import TimeStampedModel


class Participant(TimeStampedModel):
    class Genre(models.TextChoices):
        HOMME = "HOMME", "Homme"
        FEMME = "FEMME", "Femme"
        AUTRE = "AUTRE", "Autre"
        NON_PRECISE = "NON_PRECISE", "Non precise"

    class Statut(models.TextChoices):
        ACTIF = "ACTIF", "Actif"
        INACTIF = "INACTIF", "Inactif"
        ARCHIVE = "ARCHIVE", "Archive"

    matricule = models.CharField(max_length=30, unique=True, editable=False)
    nom = models.CharField(max_length=150)
    prenom = models.CharField(max_length=150)
    telephone = models.CharField(max_length=30)
    telephone_secondaire = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    genre = models.CharField(max_length=20, choices=Genre.choices, default=Genre.NON_PRECISE)
    date_naissance = models.DateField(null=True, blank=True)
    adresse = models.TextField(blank=True)
    ville = models.CharField(max_length=150, blank=True)
    pays = models.CharField(max_length=100, default="Mali")
    profession = models.CharField(max_length=150, blank=True)
    entreprise = models.CharField(max_length=255, blank=True)
    personne_contact = models.CharField(max_length=255, blank=True)
    telephone_contact = models.CharField(max_length=30, blank=True)
    photo = models.ImageField(upload_to="participants/photos/", null=True, blank=True)
    notes = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.ACTIF)

    def save(self, *args, **kwargs):
        if not self.matricule:
            self.matricule = (
                f"PAR-{timezone.localdate():%Y%m%d}-{uuid4().hex[:6].upper()}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.matricule} - {self.nom_complet}"

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}".strip()

    @property
    def total_paye(self):
        return self.inscriptions.aggregate(total=Sum("paiements__montant"))["total"] or 0


class DocumentParticipant(TimeStampedModel):
    class TypeDocument(models.TextChoices):
        CNI = "CNI", "Carte nationale d'identite"
        PASSEPORT = "PASSEPORT", "Passeport"
        PHOTO = "PHOTO", "Photo"
        DIPLOME = "DIPLOME", "Diplome"
        AUTRE = "AUTRE", "Autre"

    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="documents")
    type_document = models.CharField(max_length=30, choices=TypeDocument.choices)
    titre = models.CharField(max_length=255)
    fichier = models.FileField(upload_to="participants/documents/")
    date_expiration = models.DateField(null=True, blank=True)
    observations = models.TextField(blank=True)
