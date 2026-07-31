from django.core.validators import RegexValidator
from django.db import models

from core.models import OrganisationOwnedModel, TimeStampedModel

hex_color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Saisissez une couleur au format #RRGGBB.",
)


class ConfigurationOrganisation(OrganisationOwnedModel, TimeStampedModel):
    class Palette(models.TextChoices):
        BALYS = "BALYS", "BALY'S Group"
        OCEAN = "OCEAN", "Ocean corporate"
        EMERALD = "EMERALD", "Emerald finance"
        BORDEAUX = "BORDEAUX", "Bordeaux premium"
        CUSTOM = "CUSTOM", "Personnalise"

    nom = models.CharField(max_length=255, default="")
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
    palette = models.CharField(
        max_length=20,
        choices=Palette.choices,
        default=Palette.BALYS,
    )
    couleur_sidebar = models.CharField(
        max_length=7,
        default="#0b2448",
        validators=[hex_color_validator],
    )
    couleur_header = models.CharField(
        max_length=7,
        default="#ffffff",
        validators=[hex_color_validator],
    )
    couleur_primaire = models.CharField(
        max_length=7,
        default="#15519a",
        validators=[hex_color_validator],
    )
    couleur_secondaire = models.CharField(
        max_length=7,
        default="#102f5d",
        validators=[hex_color_validator],
    )
    couleur_accent = models.CharField(
        max_length=7,
        default="#f28b16",
        validators=[hex_color_validator],
    )
    couleur_fond = models.CharField(
        max_length=7,
        default="#f4f6f9",
        validators=[hex_color_validator],
    )
    couleur_surface = models.CharField(
        max_length=7,
        default="#ffffff",
        validators=[hex_color_validator],
    )
