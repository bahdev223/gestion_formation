from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from comptes.models import Compte, MouvementCompte, RoleCompte, TypeCompte
from core.testing import souscrire_plan_complet
from documents.models import DocumentGenere
from formations.models import CategorieFormation, Formation, SessionFormation
from inscriptions.models import Inscription
from organisations.models import Organisation
from paiements.models import Paiement
from paiements.services.mouvement_sync_service import ensure_payment_movement
from paiements.services.paiement_service import cancel_payment
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
        cls.caisse = Compte.objects.create(
            organisation=cls.organisation,
            code="CAI001",
            nom="Caisse principale",
            type=TypeCompte.ESPECES,
            role=RoleCompte.CAISSE,
            solde_actuel=Decimal("0.00"),
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
        content = response.content.decode()
        self.assertLess(
            content.index("Compte d&#x27;encaissement"),
            content.index("Mode de paiement"),
        )

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

    def test_payment_movement_sync_is_idempotent(self):
        paiement = Paiement.objects.create(
            organisation=self.organisation,
            inscription=self.inscription,
            montant=Decimal("2500.00"),
            mode_paiement=Paiement.ModePaiement.MOBILE_MONEY,
            compte=self.compte,
            reference_transaction="TX-IDEMPOTENT",
            enregistre_par=self.user,
        )

        first = ensure_payment_movement(paiement, user=self.user)
        second = ensure_payment_movement(paiement, user=self.user)

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.mouvement.pk, second.mouvement.pk)
        self.assertEqual(
            MouvementCompte.objects.filter(object_id=paiement.pk).count(),
            1,
        )
        self.compte.refresh_from_db()
        self.assertEqual(self.compte.solde_actuel, Decimal("3100.00"))

    def test_cancel_payment_reverses_financial_movement(self):
        paiement = Paiement.objects.create(
            organisation=self.organisation,
            inscription=self.inscription,
            montant=Decimal("2000.00"),
            mode_paiement=Paiement.ModePaiement.MOBILE_MONEY,
            compte=self.compte,
            reference_transaction="TX-CANCEL",
            enregistre_par=self.user,
        )
        ensure_payment_movement(paiement, user=self.user)

        cancel_payment(paiement, "Erreur de saisie", self.user)

        self.compte.refresh_from_db()
        self.assertEqual(self.compte.solde_actuel, Decimal("600.00"))
        self.assertEqual(
            MouvementCompte.objects.filter(object_id=paiement.pk).count(),
            1,
        )
        self.assertEqual(paiement.motif_annulation, "Erreur de saisie")
        self.assertTrue(
            MouvementCompte.objects.filter(
                mouvement_parent__object_id=paiement.pk,
                montant=Decimal("2000.00"),
            ).exists()
        )

    def test_payment_mode_must_match_financial_account_type(self):
        response = self.client.post(
            "/o/centre-paiements/paiements/create/",
            {
                "inscription": self.inscription.pk,
                "montant": "1000",
                "date_paiement": "2026-08-01T11:12",
                "mode_paiement": Paiement.ModePaiement.ESPECES,
                "compte": self.compte.pk,
                "reference_transaction": "TX-BAD",
                "payeur_nom": "FATOUMATA BAH",
                "observations": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Le mode ne correspond pas au compte choisi")
        self.assertFalse(Paiement.objects.filter(reference_transaction="TX-BAD").exists())

    def test_payment_index_exposes_receipt_generation_action(self):
        paiement = Paiement.objects.create(
            organisation=self.organisation,
            inscription=self.inscription,
            montant=Decimal("2500.00"),
            mode_paiement=Paiement.ModePaiement.ESPECES,
            compte=self.caisse,
            enregistre_par=self.user,
        )

        response = self.client.get("/o/centre-paiements/paiements/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Générer le reçu PDF")
        self.assertContains(response, str(paiement.pk))

    def test_receipt_generation_uses_payment_document_flow(self):
        paiement = Paiement.objects.create(
            organisation=self.organisation,
            inscription=self.inscription,
            montant=Decimal("2500.00"),
            mode_paiement=Paiement.ModePaiement.ESPECES,
            compte=self.caisse,
            enregistre_par=self.user,
        )

        response = self.client.post(
            "/o/centre-paiements/documents/generer/recu/",
            {"paiement_id": paiement.pk},
        )

        self.assertEqual(response.status_code, 302)
        document = DocumentGenere.objects.get(reference=paiement.numero_recu)
        self.assertEqual(document.organisation, self.organisation)
        self.assertTrue(document.fichier.name.endswith(".pdf"))
