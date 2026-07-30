"""Tests for dashboard views."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.models import ConfigurationOrganisation
from django_paie.models import EcheanceSalariale
from django_rh.models import Employee
from organisations.models import Organisation


class OrganisationSettingsThemeViewTest(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="theme-admin",
            email="theme@example.com",
            password="test-password",
        )
        self.client.force_login(self.admin)
        self.organisation = Organisation.objects.create(
            nom="Client Demo",
            slug="client-demo",
            email="contact@client-demo.test",
            telephone="+22370000000",
        )

    def test_theme_colors_are_rendered_in_global_css(self):
        ConfigurationOrganisation.objects.create(
            organisation=self.organisation,
            nom="Client Demo",
            couleur_sidebar="#123456",
            couleur_header="#fefefe",
            couleur_primaire="#0f766e",
            couleur_secondaire="#115e59",
            couleur_accent="#ca8a04",
            couleur_fond="#f8fafc",
            couleur_surface="#ffffff",
        )

        response = self.client.get(
            reverse(
                "organisations:dashboard:organisation-settings",
                kwargs={"organisation_slug": self.organisation.slug},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "--baly-blue-deep: #123456")
        self.assertContains(response, "--baly-header: #fefefe")


class PayrollGenerateViewTest(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="payroll-admin",
            email="payroll@example.com",
            password="test-password",
        )
        self.organisation = Organisation.objects.create(
            nom="Client Paie",
            slug="client-paie",
            email="contact@client-paie.test",
            telephone="+22370000001",
        )
        # Les modules paie et RH sont optionnels : ils exigent un abonnement.
        from core.testing import souscrire_plan_complet

        souscrire_plan_complet(self.organisation)
        self.employee = Employee.objects.create(
            organisation=self.organisation,
            matricule="TEST-PAIE-001",
            first_name="Mariam",
            last_name="Barry",
            status=Employee.Status.ACTIVE,
            salaire_mensuel=750000,
            created_by=self.admin,
        )
        self.client.force_login(self.admin)
        self.url = reverse(
            "organisations:dashboard:payroll-generate",
            kwargs={"organisation_slug": self.organisation.slug},
        )

    def test_generation_accepte_valeur_html_month(self):
        response = self.client.post(self.url, {"periode": "2026-07"})

        self.assertRedirects(
            response,
            reverse(
                "organisations:paie:echeance-list",
                kwargs={"organisation_slug": self.organisation.slug},
            ),
        )
        echeance = EcheanceSalariale.objects.get()
        self.assertEqual((echeance.mois, echeance.annee), (7, 2026))

    def test_generation_refuse_annee_courte_sans_erreur_integrite(self):
        response = self.client.post(self.url, {"periode": "07/26"}, follow=True)

        self.assertRedirects(
            response,
            reverse(
                "organisations:paie:dashboard",
                kwargs={"organisation_slug": self.organisation.slug},
            ),
        )
        self.assertContains(response, "entre 2000 et 2100")
        self.assertFalse(EcheanceSalariale.objects.exists())
