from django.contrib import admin

from .models import ConfigurationOrganisation


@admin.register(ConfigurationOrganisation)
class ConfigurationOrganisationAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "email", "devise", "palette", "updated_at")
    fieldsets = (
        (
            "Identite",
            {
                "fields": (
                    "nom",
                    "logo",
                    "adresse",
                    "telephone",
                    "email",
                    "site_web",
                    "numero_fiscal",
                    "devise",
                )
            },
        ),
        (
            "Documents",
            {
                "fields": (
                    "prefixe_recu",
                    "prefixe_attestation",
                    "signature_nom",
                    "signature_fonction",
                    "signature_image",
                    "cachet_image",
                )
            },
        ),
        (
            "Charte graphique",
            {
                "fields": (
                    "palette",
                    "couleur_sidebar",
                    "couleur_header",
                    "couleur_primaire",
                    "couleur_secondaire",
                    "couleur_accent",
                    "couleur_fond",
                    "couleur_surface",
                )
            },
        ),
    )
