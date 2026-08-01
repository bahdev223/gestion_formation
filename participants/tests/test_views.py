"""Tests for participants views."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.testing import souscrire_plan_complet
from organisations.models import Organisation
from participants.models import Participant


class ParticipantIndexViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            username="participant-index-admin",
            email="participant-index@example.test",
            password="test1234",
        )
        cls.organisation = Organisation.objects.create(
            nom="Centre Participants",
            slug="centre-participants",
            email="contact@participants.test",
            telephone="+22370000008",
        )
        souscrire_plan_complet(cls.organisation)
        cls.participant = Participant.objects.create(
            organisation=cls.organisation,
            prenom="Fatoumata",
            nom="Bah",
            telephone="+22370000009",
            email="fatoumata@example.test",
            profession="Assistante",
            entreprise="OHT Service",
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_index_renders_operational_register(self):
        response = self.client.get("/o/centre-participants/participants/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fatoumata Bah")
        self.assertContains(response, "OHT Service")
        self.assertContains(response, "Apprenants")
        self.assertContains(response, "Inscriptions")

    def test_index_can_filter_by_search(self):
        response = self.client.get(
            "/o/centre-participants/participants/",
            {"q": "OHT"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fatoumata Bah")
