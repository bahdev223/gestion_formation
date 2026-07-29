from django.db import models

from core.models import TimeStampedModel


class ConfigurationOrganisation(TimeStampedModel):
    nom = models.CharField(max_length=255, default="BALY'S GROUP")
    logo = models.ImageField(upload_to="settings/", null=True, blank=True)
    adresse = models.TextField(blank=True)
    telephone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    site_web = models.URLField(blank=True)
    numero_fiscal = models.CharField(max_length=100, blank=True)
    devise = models.CharField(max_length=10, default="FCFA")
    prefixe_recu = models.CharField(max_length=10, default="REC")
    prefixe_attestation = models.CharField(max_length=10, default="ATT")
    signature_nom = models.CharField(max_length=255, blank=True)
    signature_fonction = models.CharField(max_length=255, blank=True)
    signature_image = models.ImageField(upload_to="settings/signatures/", null=True, blank=True)
    cachet_image = models.ImageField(upload_to="settings/cachets/", null=True, blank=True)

