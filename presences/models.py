from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import OrganisationOwnedModel, TimeStampedModel


class Presence(OrganisationOwnedModel, TimeStampedModel):
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
        ordering = ["seance__date", "inscription__participant__nom"]
        constraints = [
            models.UniqueConstraint(
                fields=["seance", "inscription"],
                name="unique_presence_seance_inscription",
            )
        ]
        indexes = [
            models.Index(fields=["seance", "statut"]),
            models.Index(fields=["inscription", "statut"]),
        ]

    def clean(self):
        super().clean()
        if (
            self.seance_id
            and self.inscription_id
            and self.seance.session_id != self.inscription.session_id
        ):
            raise ValidationError(
                "L'inscription doit appartenir à la session de la séance."
            )

    def __str__(self):
        return (
            f"{self.inscription.participant.nom_complet} — "
            f"{self.seance.titre} — {self.get_statut_display()}"
        )
