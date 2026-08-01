from django.contrib.auth import get_user_model
from django.test import TestCase

from core.testing import souscrire_plan_complet
from organisations.models import MembreOrganisation, Organisation


class GrandLivreViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            username="grand-livre-admin",
            email="grand-livre@example.test",
            password="test1234",
        )
        cls.organisation = Organisation.objects.create(
            nom="Centre Grand Livre",
            slug="centre-grand-livre",
            email="contact@grand-livre.test",
            telephone="+22370000000",
            statut=Organisation.Statut.ACTIVE,
        )
        MembreOrganisation.objects.create(
            organisation=cls.organisation,
            user=cls.user,
            role=MembreOrganisation.Role.PROPRIETAIRE,
        )
        souscrire_plan_complet(cls.organisation)

    def test_grand_livre_uses_current_tenant(self):
        self.client.force_login(self.user)
        response = self.client.get(
            f"/o/{self.organisation.slug}/comptabilite/grand-livre/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Grand livre")
