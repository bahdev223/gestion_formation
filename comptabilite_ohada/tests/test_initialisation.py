from django.test import TestCase

from organisations.models import Organisation

from ..models import (
    CompteComptable,
)
from ..services.initialisation_service import InitialisationService


class InitialisationServiceTest(TestCase):
    def setUp(self):
        self.service = InitialisationService()

    def test_charger_plan_comptable(self):
        result = self.service.charger_plan_comptable()
        self.assertTrue(result.get("success"))
        self.assertGreater(CompteComptable.objects.count(), 0)

    def test_charger_plan_comptable_ecraser(self):
        CompteComptable.objects.create(code="571", libelle="Old", nature="DEBIT")
        CompteComptable.objects.create(
            code="CUSTOM-001",
            libelle="Compte personnalise",
            nature="DEBIT",
        )
        self.assertEqual(CompteComptable.objects.count(), 2)
        result = self.service.charger_plan_comptable(force=True)
        self.assertTrue(result.get("success"))
        self.assertGreater(CompteComptable.objects.count(), 50)
        compte = CompteComptable.objects.get(code="571")
        self.assertEqual(compte.libelle, "CAISSE SIEGE SOCIAL")
        self.assertTrue(CompteComptable.objects.filter(code="CUSTOM-001").exists())

    def test_chaque_entreprise_recoit_un_plan_independant(self):
        entreprise_a = Organisation.objects.create(
            nom="Entreprise A", slug="entreprise-a", email="a@test.test"
        )
        entreprise_b = Organisation.objects.create(
            nom="Entreprise B", slug="entreprise-b", email="b@test.test"
        )
        self.service.initialiser_organisation(entreprise_a)
        self.service.initialiser_organisation(entreprise_b)

        caisse_a = CompteComptable.objects.get(
            organisation=entreprise_a, code="571"
        )
        caisse_b = CompteComptable.objects.get(
            organisation=entreprise_b, code="571"
        )
        caisse_a.libelle = "Caisse agence A"
        caisse_a.save(update_fields=["libelle"])

        caisse_b.refresh_from_db()
        self.assertEqual(caisse_b.libelle, "CAISSE SIEGE SOCIAL")
