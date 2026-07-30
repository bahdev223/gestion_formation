from django.contrib.auth import get_user_model
from django.test import TestCase

from organisations.models import MembreOrganisation, Organisation
from subscriptions.models import Abonnement


class PlatformSignupTest(TestCase):
    def test_landing_publique_est_accessible(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Créer mon entreprise")
        self.assertNotContains(response, "python manage.py")
        self.assertNotContains(response, "/o/votre-entreprise/")

    def test_creation_entreprise_connecte_et_redirige_vers_slug(self):
        response = self.client.post(
            "/creer-entreprise/",
            {
                "organisation_nom": "Beta Academy",
                "organisation_email": "contact@beta.test",
                "organisation_telephone": "+22370000000",
                "ville": "Bamako",
                "pays": "Mali",
                "first_name": "Awa",
                "last_name": "Traore",
                "email": "awa@beta.test",
                "matricule": "BETA-ADMIN",
                "password1": "secret1234",
                "password2": "secret1234",
            },
        )

        self.assertRedirects(
            response,
            "/o/beta-academy/dashboard/",
            fetch_redirect_response=False,
        )
        organisation = Organisation.objects.get(slug="beta-academy")
        user = get_user_model().objects.get(username="BETA-ADMIN")
        self.assertTrue(
            MembreOrganisation.objects.filter(
                organisation=organisation,
                user=user,
                role=MembreOrganisation.Role.PROPRIETAIRE,
            ).exists()
        )
        self.assertTrue(
            Abonnement.objects.filter(
                organisation=organisation,
                statut=Abonnement.Statut.ESSAI,
            ).exists()
        )
