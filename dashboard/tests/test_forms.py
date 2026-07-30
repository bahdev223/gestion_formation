"""Tests for dashboard forms."""

from django.test import TestCase

from dashboard.forms import ConfigurationOrganisationForm


class ConfigurationOrganisationFormTest(TestCase):
    def test_refuse_couleur_invalide(self):
        form = ConfigurationOrganisationForm(
            data={
                "nom": "Entreprise Test",
                "devise": "FCFA",
                "prefixe_recu": "REC",
                "prefixe_attestation": "ATT",
                "palette": "CUSTOM",
                "couleur_sidebar": "bleu",
                "couleur_header": "#ffffff",
                "couleur_primaire": "#15519a",
                "couleur_secondaire": "#102f5d",
                "couleur_accent": "#f28b16",
                "couleur_fond": "#f4f6f9",
                "couleur_surface": "#ffffff",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("couleur_sidebar", form.errors)
