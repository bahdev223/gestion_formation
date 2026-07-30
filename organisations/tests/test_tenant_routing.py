from django.contrib.auth import get_user_model
from django.test import TestCase

from organisations.models import Organisation


class TenantRoutingTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation = Organisation.objects.create(
            nom="Centre Alpha",
            slug="centre-alpha",
            email="contact@alpha.test",
            telephone="+22300000000",
        )
        cls.user = get_user_model().objects.create_superuser(
            username="route-admin",
            email="route-admin@alpha.test",
            password="test1234",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_anciens_chemins_metier_ne_sont_plus_accessibles(self):
        legacy_paths = [
            "/formations/",
            "/participants/",
            "/inscriptions/",
            "/paiements/",
            "/presences/",
            "/documents/",
            "/paie-salariale/",
            "/ressources-humaines/",
            "/comptabilite/",
            "/comptes-financiers/",
            "/app/",
        ]

        for path in legacy_paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_liens_dashboard_contiennent_toujours_le_slug_entreprise(self):
        response = self.client.get("/o/centre-alpha/dashboard/")

        self.assertEqual(response.status_code, 200)
        for module in (
            "formations",
            "participants",
            "inscriptions",
            "paiements",
            "presences",
            "documents",
            "comptabilite",
            "comptes-financiers",
        ):
            self.assertContains(response, f'/o/centre-alpha/{module}/')
            self.assertNotContains(response, f'href="/{module}/')

    def test_page_inscriptions_est_servie_uniquement_dans_entreprise(self):
        response = self.client.get("/o/centre-alpha/inscriptions/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/o/centre-alpha/inscriptions/create/")
