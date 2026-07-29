from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Presence(TimeStampedModel):
    class Statut(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        RETARD = "RETARD", "Retard"
        JUSTIFIE = "JUSTIFIE", "Absence justifiee"

    seance = models.ForeignKey("formations.Seance", on_delete=models.CASCADE, related_name="presences")
    inscription = models.ForeignKey("inscriptions.Inscription", on_delete=models.CASCADE, related_name="presences")
    statut = models.CharField(max_length=20, choices=Statut.choices)
    heure_arrivee = models.TimeField(null=True, blank=True)
    heure_depart = models.TimeField(null=True, blank=True)
    motif = models.TextField(blank=True)
    observations = models.TextField(blank=True)
    enregistre_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="presences_enregistrees")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["seance", "inscription"], name="unique_presence_seance_inscription")]

