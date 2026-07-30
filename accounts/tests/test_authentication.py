from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase

from organisations.models import MembreOrganisation, Organisation


class EmailOrMatriculeLoginTest(TestCase):
    def setUp(self):
        self.organisation = Organisation.objects.create(
            nom="Alpha Formation",
            slug="alpha-formation",
            email="contact@alpha.test",
            telephone="+22300000000",
            statut=Organisation.Statut.ACTIVE,
        )
        self.user = get_user_model().objects.create_user(
            username="MAT-001",
            email="user@alpha.test",
            password="secret1234",
            role="ADMIN",
        )
        MembreOrganisation.objects.create(
            organisation=self.organisation,
            user=self.user,
            role=MembreOrganisation.Role.ADMIN,
        )

    def test_authentifie_par_email(self):
        user = authenticate(username="user@alpha.test", password="secret1234")

        self.assertEqual(user, self.user)

    def test_authentifie_par_matricule(self):
        user = authenticate(username="MAT-001", password="secret1234")

        self.assertEqual(user, self.user)

    def test_login_redirige_vers_organisation(self):
        response = self.client.post(
            "/accounts/login/",
            {"username": "user@alpha.test", "password": "secret1234"},
        )

        self.assertRedirects(
            response,
            "/o/alpha-formation/dashboard/",
            fetch_redirect_response=False,
        )

    def test_racine_redirige_vers_organisation_connectee(self):
        self.client.force_login(self.user)

        response = self.client.get("/")

        self.assertRedirects(
            response,
            "/o/alpha-formation/dashboard/",
            fetch_redirect_response=False,
        )
