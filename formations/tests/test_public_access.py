from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.testing import souscrire_plan_complet
from formations.models import (
    CategorieFormation,
    Formation,
    Seance,
    SessionAccessLink,
    SessionFormation,
)
from organisations.models import Organisation


class SessionPublicAccessTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            username="session-public-admin",
            email="session-public@example.test",
            password="test1234",
        )
        cls.organisation = Organisation.objects.create(
            nom="Centre Public",
            slug="centre-public",
            email="contact@public.test",
            telephone="+22370000007",
        )
        souscrire_plan_complet(cls.organisation)
        cls.categorie = CategorieFormation.objects.create(
            organisation=cls.organisation,
            nom="Bureautique",
        )
        cls.formation = Formation.objects.create(
            organisation=cls.organisation,
            nom="Informatique bureautique",
            categorie=cls.categorie,
            duree=10,
            prix_standard=100000,
            statut=Formation.Statut.ACTIVE,
        )
        cls.session = SessionFormation.objects.create(
            organisation=cls.organisation,
            formation=cls.formation,
            titre="La bureautique",
            formateur=cls.user,
            date_debut=date(2026, 7, 30),
            date_fin=date(2026, 8, 10),
            heure_debut=time(9, 0),
            heure_fin=time(12, 0),
            lieu="GOLF",
            capacite_max=20,
            prix_applique=100000,
            statut=SessionFormation.Statut.PLANIFIEE,
        )
        cls.seance = Seance.objects.create(
            organisation=cls.organisation,
            session=cls.session,
            titre="Introduction Word",
            date=date(2026, 7, 31),
            heure_debut=time(9, 0),
            heure_fin=time(12, 0),
            lieu="Salle 1",
        )

    def test_public_link_exposes_read_only_session_schedule(self):
        access_link = SessionAccessLink.objects.create(
            organisation=self.organisation,
            session=self.session,
        )

        response = self.client.get(
            f"/o/centre-public/formations/sessions/acces/{access_link.token}/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "La bureautique")
        self.assertContains(response, "Introduction Word")
        self.assertNotContains(response, "prix_applique")
        self.assertNotContains(response, "Paiement")

    def test_qr_endpoint_returns_svg_for_active_public_link(self):
        access_link = SessionAccessLink.objects.create(
            organisation=self.organisation,
            session=self.session,
        )

        response = self.client.get(
            f"/o/centre-public/formations/sessions/acces/{access_link.token}/qr.svg"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/svg+xml")
        self.assertIn(b"<svg", response.content)

    def test_admin_can_enable_public_access_from_session_detail(self):
        self.client.force_login(self.user)

        response = self.client.post(
            f"/o/centre-public/formations/sessions/{self.session.pk}/acces/enable/"
        )

        self.assertRedirects(
            response,
            f"/o/centre-public/formations/sessions/{self.session.pk}/",
            fetch_redirect_response=False,
        )
        access_link = SessionAccessLink.objects.get(session=self.session)
        self.assertTrue(access_link.is_active)
        self.assertIsNotNone(access_link.expires_at)

    def test_session_list_renders_operational_cards(self):
        self.client.force_login(self.user)

        response = self.client.get("/o/centre-public/formations/sessions/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "La bureautique")
        self.assertContains(response, "Informatique bureautique")
        self.assertContains(response, "Apprenants")
        self.assertContains(response, "Seances")

    def test_direct_get_on_access_action_redirects_without_changing_state(self):
        self.client.force_login(self.user)

        response = self.client.get(
            f"/o/centre-public/formations/sessions/{self.session.pk}/acces/enable/"
        )

        self.assertRedirects(
            response,
            f"/o/centre-public/formations/sessions/{self.session.pk}/",
            fetch_redirect_response=False,
        )
        self.assertFalse(SessionAccessLink.objects.filter(session=self.session).exists())
