from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel


class Attestation(TimeStampedModel):
    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", "Brouillon"
        GENEREE = "GENEREE", "Generee"
        ANNULEE = "ANNULEE", "Annulee"

    numero = models.CharField(max_length=30, unique=True, editable=False)
    inscription = models.OneToOneField("inscriptions.Inscription", on_delete=models.PROTECT, related_name="attestation")
    date_delivrance = models.DateField(default=timezone.localdate)
    nom_participant = models.CharField(max_length=255)
    nom_formation = models.CharField(max_length=255)
    titre_session = models.CharField(max_length=255)
    date_debut = models.DateField()
    date_fin = models.DateField()
    duree_texte = models.CharField(max_length=100)
    formateur_nom = models.CharField(max_length=255)
    taux_presence = models.DecimalField(max_digits=5, decimal_places=2)
    fichier_pdf = models.FileField(upload_to="documents/attestations/", null=True, blank=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.BROUILLON)
    generee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    motif_annulation = models.TextField(blank=True)


class DocumentGenere(TimeStampedModel):
    class TypeDocument(models.TextChoices):
        RECU = "RECU", "Recu de paiement"
        ATTESTATION = "ATTESTATION", "Attestation"
        LISTE_PARTICIPANTS = "LISTE_PARTICIPANTS", "Liste des participants"
        FEUILLE_PRESENCE = "FEUILLE_PRESENCE", "Feuille de presence"
        RAPPORT_SESSION = "RAPPORT_SESSION", "Rapport de session"

    type_document = models.CharField(max_length=30, choices=TypeDocument.choices)
    reference = models.CharField(max_length=100)
    fichier = models.FileField(upload_to="documents/generated/")
    genere_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    metadata = models.JSONField(default=dict, blank=True)

