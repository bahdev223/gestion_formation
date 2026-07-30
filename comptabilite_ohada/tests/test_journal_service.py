from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import (
    CompteComptable, JournalComptable, ExerciceComptable,
    EcritureComptable, LigneEcritureComptable,
)
from organisations.models import Organisation

from ..services.journal_service import BalanceService


class BalanceServiceTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="compta", password="test1234"
        )
        self.organisation = Organisation.objects.create(
            nom="Centre Balance",
            slug="centre-balance",
            email="balance@test.test",
            telephone="+22300000000",
        )
        self.autre_organisation = Organisation.objects.create(
            nom="Centre Voisin",
            slug="centre-voisin",
            email="voisin@test.test",
            telephone="+22300000001",
        )
        self.journal = JournalComptable.objects.create(
            code="VN", libelle="Ventes", type_journal="VN"
        )
        self.exercice = ExerciceComptable.objects.create(
            code="2025",
            date_debut="2025-01-01", date_fin="2025-12-31",
            organisation=self.organisation,
        )
        self.compte_caisse = CompteComptable.objects.create(
            code="571", libelle="Caisse", nature="DEBIT", type_compte="compte",
        )
        self.compte_produit = CompteComptable.objects.create(
            code="701", libelle="Ventes", nature="CREDIT", type_compte="compte",
        )
        self.compte_charge = CompteComptable.objects.create(
            code="601", libelle="Achats", nature="DEBIT", type_compte="compte",
        )

    def _ecriture(self, organisation, reference):
        ecriture = EcritureComptable.objects.create(
            journal=self.journal, exercice=self.exercice,
            date_ecriture="2025-06-01", reference=reference,
            libelle="Vente", validee=True, created_by=self.user.username,
            organisation=organisation,
        )
        LigneEcritureComptable.objects.create(
            ecriture=ecriture, compte=self.compte_caisse, debit=100000,
        )
        LigneEcritureComptable.objects.create(
            ecriture=ecriture, compte=self.compte_produit, credit=100000,
        )
        return ecriture

    def test_balance_vide(self):
        balance = BalanceService().balance(
            organisation=self.organisation, exercice=self.exercice
        )
        self.assertEqual(len(balance), 0)

    def test_balance_apres_ecritures(self):
        self._ecriture(self.organisation, "VN-001")

        balance = BalanceService().balance(
            organisation=self.organisation, exercice=self.exercice
        )
        self.assertGreaterEqual(len(balance), 2)

    def test_balance_ignore_les_ecritures_dune_autre_organisation(self):
        """La balance ne doit jamais consolider plusieurs clients."""
        self._ecriture(self.autre_organisation, "VN-VOISIN")

        balance = BalanceService().balance(
            organisation=self.organisation, exercice=self.exercice
        )
        self.assertEqual(len(balance), 0)

    def test_balance_exige_une_organisation(self):
        with self.assertRaises(TypeError):
            BalanceService().balance(exercice=self.exercice)
