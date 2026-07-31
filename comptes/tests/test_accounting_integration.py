from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from comptabilite_ohada.models import EcritureComptable, ExerciceComptable
from comptabilite_ohada.services.initialisation_service import InitialisationService
from comptes.models import Compte, MouvementCompte, SensMouvement
from comptes.services import MouvementCompteService, TransfertCompteService
from organisations.models import Organisation


class FinancialAccountingIntegrationTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin-finance",
            password="test1234",
        )
        InitialisationService.charger_plan_comptable()
        InitialisationService.initialiser_journaux()
        # Le pont evenementiel deduit desormais le tenant du compte de
        # tresorerie mouvemente, et l'exercice doit appartenir au meme.
        self.organisation = Organisation.objects.create(
            nom="Centre Tresorerie",
            slug="centre-tresorerie",
            email="tresorerie@test.test",
            telephone="+22300000000",
        )
        year = date.today().year
        ExerciceComptable.objects.create(
            code=str(year),
            date_debut=date(year, 1, 1),
            date_fin=date(year, 12, 31),
            organisation=self.organisation,
        )
        self.caisse = Compte.objects.create(
            code="CAISSE-T",
            nom="Caisse test",
            type="ESPECES",
            solde_actuel=Decimal("100000"),
            compte_comptable_code="571",
            organisation=self.organisation,
        )
        self.banque = Compte.objects.create(
            code="BANQUE-T",
            nom="Banque test",
            type="BANQUE",
            solde_actuel=Decimal("0"),
            compte_comptable_code="521",
            organisation=self.organisation,
        )

    def test_encaissement_met_a_jour_solde_et_comptabilite(self):
        MouvementCompteService.encaisser(
            self.caisse,
            "25000",
            "Paiement formation",
            self.user,
            reference="REC-T",
        )
        self.caisse.refresh_from_db()
        self.assertEqual(self.caisse.solde_actuel, Decimal("125000"))
        self.assertEqual(EcritureComptable.objects.count(), 1)
        self.assertTrue(EcritureComptable.objects.get().est_equilibree)

    def test_transfert_debite_source_credite_destination_une_seule_fois(self):
        TransfertCompteService.transferer(
            self.caisse,
            self.banque,
            "40000",
            self.user,
            notes="Dépôt banque",
        )
        self.caisse.refresh_from_db()
        self.banque.refresh_from_db()
        self.assertEqual(self.caisse.solde_actuel, Decimal("60000"))
        self.assertEqual(self.banque.solde_actuel, Decimal("40000"))
        self.assertEqual(MouvementCompte.objects.count(), 2)
        self.assertEqual(
            set(MouvementCompte.objects.values_list("sens", flat=True)),
            {SensMouvement.ENTREE, SensMouvement.SORTIE},
        )
        self.assertEqual(EcritureComptable.objects.count(), 1)
        self.assertTrue(EcritureComptable.objects.get().est_equilibree)
