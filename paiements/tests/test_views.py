from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from comptes.models import Compte, MouvementCompte, RoleCompte, TypeCompte
from core.testing import souscrire_plan_complet
from formations.models import CategorieFormation, Formation, SessionFormation
from inscriptions.models import Inscription
from organisations.models import Organisation
from paiements.models import Paiement
from participants.models import Participant


class PaiementCreateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(
            username="paiement-admin",
            email="paiement-admin@example.test",
            password="test1234",
        )
        cls.organisation = Organisation.objects.create(
            nom="Centre Paiements",
            slug="centre-paiements",
            email="contact@paiements.test",
            telephone="+22370000010",
            devise="EUR",
        )
        souscrire_plan_complet(cls.organisation)
        cls.compte = Compte.objects.create(
            organisation=cls.organisation,
            code="MM001",
            nom="Compte mobile principal",
            type=TypeCompte.MOBILE_MONEY,
            role=RoleCompte.ENCAISSEMENT,
            solde_actuel=Decimal("600.00"),
        )
        cls.categorie = CategorieFormation.objects.create(
            organisation=cls.organisation,
            nom="Gestion",
        )
        cls.formation = Formation.objects.create(
            organisation=cls.organisation,
            nom="Gestion de projet",
            categorie=cls.categorie,
            duree=5,
            prix_standard=Decimal("100000.00"),
            statut=Formation.Statut.ACTIVE,
        )
        cls.session = SessionFormation.objects.create(
            organisation=cls.organisation,
            formation=cls.formation,
            titre="Session projet",
            formateur=cls.user,
            date_debut=date(2026, 8, 1),
            date_fin=date(2026, 8, 5),
            lieu="Salle A",
            capacite_max=20,
            prix_applique=Decimal("100000.00"),
            statut=SessionFormation.Statut.PLANIFIEE,
        )
        cls.participant = Participant.objects.create(
            organisation=cls.organisation,
            prenom="Fatoumata",
            nom="Bah",
            telephone="+22370000011",
        )
        cls.inscription = Inscription.objects.create(
            organisation=cls.organisation,
            participant=cls.participant,
            session=cls.session,
            prix_initial=Decimal("100000.00"),
            remise=Decimal("0.00"),
            montant_final=Decimal("100000.00"),
            cree_par=cls.user,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_create_form_separates_payment_mode_account_and_balance(self):
        response = self.client.get("/o/centre-paiements/paiements/create/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mode de paiement")
        self.assertContains(response, "Paiement mobile")
        self.assertContains(response, "Compte d&#x27;encaissement")
        self.assertContains(response, "Compte mobile principal")
        self.assertContains(response, "Reste à payer")
        self.assertContains(response, "100000")
        self.assertContains(response, "Ex : 1 500")
        self.assertContains(response, "Montant encaissé (EUR)")
        self.assertContains(response, "EUR")
        self.assertNotContains(response, "Montant encaissé (FCFA)")
        self.assertNotContains(response, "Orange Money")
        self.assertNotContains(response, "Moov Money")
        self.assertNotContains(response, 'step="500"')

    def test_create_payment_updates_financial_account(self):
        response = self.client.post(
            "/o/centre-paiements/paiements/create/",
            {
                "inscription": self.inscription.pk,
                "montant": "1 000",
                "date_paiement": "2026-08-01T11:12",
                "mode_paiement": Paiement.ModePaiement.MOBILE_MONEY,
                "compte": self.compte.pk,
                "reference_transaction": "TX-001",
                "payeur_nom": "FATOUMATA BAH",
                "observations": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        paiement = Paiement.objects.get(reference_transaction="TX-001")
        self.assertEqual(paiement.compte, self.compte)
        self.assertEqual(paiement.mode_paiement, Paiement.ModePaiement.MOBILE_MONEY)

        self.compte.refresh_from_db()
        self.assertEqual(self.compte.solde_actuel, Decimal("1600.00"))

        mouvement = MouvementCompte.objects.get(object_id=paiement.pk)
        self.assertEqual(mouvement.compte, self.compte)
        self.assertEqual(mouvement.montant, Decimal("1000.00"))

        self.inscription.refresh_from_db()
        self.assertEqual(
            self.inscription.statut_paiement,
            Inscription.StatutPaiement.PARTIEL,
        )
