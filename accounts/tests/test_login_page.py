"""Page de connexion : ergonomie et respect de la destination demandee."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.views import UserLoginView
from organisations.models import MembreOrganisation, Organisation


class PageConnexionTest(TestCase):
    def test_le_champ_mot_de_passe_a_une_bascule_afficher_masquer(self):
        response = self.client.get("/accounts/login/")
        body = response.content.decode()

        self.assertEqual(response.status_code, 200)
        # La bascule est declarative (Alpine) : le type de l'input est lie.
        self.assertIn(":type=\"visible ? 'text' : 'password'\"", body)
        # Le bouton ne doit pas soumettre le formulaire.
        self.assertIn('type="button"', body)
        # Etats accessibles, avec un repli sans JavaScript.
        self.assertIn("aria-pressed", body)
        self.assertIn("Afficher le mot de passe", body)

    def test_la_page_reste_concise(self):
        """La version precedente noyait le formulaire sous les explications."""
        response = self.client.get("/accounts/login/")
        body = response.content.decode()

        for bavardage in (
            "Accès sécurisé",
            "Formix vous dirigera vers votre entreprise",
            "Accès plateforme",
        ):
            with self.subTest(texte=bavardage):
                self.assertNotIn(bavardage, body)

    def test_le_bouton_connexion_de_la_barre_publique_est_masque(self):
        """Proposer « Connexion » sur la page de connexion n'a pas de sens."""
        page_connexion = self.client.get("/accounts/login/").content.decode()
        autre_page = self.client.get("/").content.decode()

        # La barre publique existe ailleurs...
        self.assertIn('href="/accounts/login/"', autre_page)
        # ...mais pas sur la page de connexion elle-meme.
        self.assertNotIn('href="/accounts/login/"', page_connexion)


class RedirectionApresConnexionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation = Organisation.objects.create(
            nom="Centre Redirection",
            slug="centre-redirection",
            email="redir@test.test",
            telephone="+22300000000",
            statut=Organisation.Statut.ACTIVE,
        )
        cls.user = get_user_model().objects.create_user(
            username="redir-user",
            email="redir@user.test",
            password="secret1234",
        )
        MembreOrganisation.objects.create(
            organisation=cls.organisation,
            user=cls.user,
            role=MembreOrganisation.Role.ADMIN,
        )

    def test_le_formulaire_transmet_la_destination_demandee(self):
        response = self.client.get("/accounts/login/?next=/o/centre-redirection/documents/")
        self.assertContains(
            response,
            'name="next" value="/o/centre-redirection/documents/"',
        )

    def test_la_destination_demandee_gagne_sur_la_redirection_par_role(self):
        """Sans cela, un utilisateur envoye vers une page precise par un
        middleware atterrissait sur son tableau de bord."""
        cible = "/o/centre-redirection/documents/"
        response = self.client.post(
            "/accounts/login/",
            {"username": "redir@user.test", "password": "secret1234", "next": cible},
        )
        self.assertRedirects(response, cible, fetch_redirect_response=False)

    def test_sans_destination_la_redirection_par_role_sapplique(self):
        response = self.client.post(
            "/accounts/login/",
            {"username": "redir@user.test", "password": "secret1234"},
        )
        self.assertRedirects(
            response,
            "/o/centre-redirection/dashboard/",
            fetch_redirect_response=False,
        )

    def test_se_souvenir_de_moi_prolonge_la_session(self):
        """La case ne doit pas etre decorative."""
        self.client.post(
            "/accounts/login/",
            {
                "username": "redir@user.test",
                "password": "secret1234",
                "remember_me": "1",
            },
        )
        self.assertEqual(
            self.client.session.get_expiry_age(),
            UserLoginView.REMEMBER_ME_SECONDS,
        )

    def test_sans_la_case_la_session_expire_a_la_fermeture(self):
        self.client.post(
            "/accounts/login/",
            {"username": "redir@user.test", "password": "secret1234"},
        )
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_une_destination_externe_est_ignoree(self):
        """Protection contre la redirection ouverte."""
        response = self.client.post(
            "/accounts/login/",
            {
                "username": "redir@user.test",
                "password": "secret1234",
                "next": "https://exemple-malveillant.test/phishing",
            },
        )
        self.assertRedirects(
            response,
            "/o/centre-redirection/dashboard/",
            fetch_redirect_response=False,
        )
