"""Les pages d'operations rendent, s'adaptent au type, et restent isolees."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from comptabilite_ohada.models import ExerciceComptable
from comptabilite_ohada.services.initialisation_service import InitialisationService
from comptes.models import Compte
from operations.models import Operation
from organisations.models import MembreOrganisation, Organisation


def creer_organisation(nom, slug):
    return Organisation.objects.create(
        nom=nom,
        slug=slug,
        email=f"{slug}@test.test",
        telephone="+22300000000",
        statut=Organisation.Statut.ACTIVE,
    )


class VuesOperationTest(TestCase):
    def setUp(self):
        InitialisationService.charger_plan_comptable()
        InitialisationService.initialiser_journaux()

        self.organisation = creer_organisation("Centre Vues", "centre-vues")
        annee = date.today().year
        ExerciceComptable.objects.create(
            code=f"CV-{annee}",
            date_debut=date(annee, 1, 1),
            date_fin=date(annee, 12, 31),
            organisation=self.organisation,
        )
        self.caisse = Compte.objects.create(
            code="CAISSE-V",
            nom="Caisse vues",
            type="ESPECES",
            solde_actuel=Decimal("100000"),
            compte_comptable_code="571",
            organisation=self.organisation,
        )
        self.user = get_user_model().objects.create_user(
            username="vue-admin", password="test1234"
        )
        self.member = MembreOrganisation.objects.create(
            organisation=self.organisation,
            user=self.user,
            role=MembreOrganisation.Role.ADMIN,
        )
        self.client.force_login(self.user)
        self.base = f"/o/{self.organisation.slug}/operations/"

    def test_la_liste_saffiche(self):
        reponse = self.client.get(self.base)
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Aucune opération enregistrée")
        self.assertContains(reponse, "Entrées")
        self.assertContains(reponse, "Sorties")

    def test_le_formulaire_saffiche_sans_type_choisi(self):
        reponse = self.client.get(f"{self.base}nouvelle/")
        self.assertEqual(reponse.status_code, 200)
        corps = reponse.content.decode()
        # Sans type, on ne demande que le socle : pas de compte de trésorerie.
        self.assertIn("Choisissez un type", corps)
        self.assertNotIn('name="compte_tresorerie"', corps)
        self.assertNotIn("{# Le champ", corps)
        self.assertIn(f"Montant ({self.organisation.devise})", corps)
        self.assertIn("Enregistrer l’opération", corps)
        self.assertNotIn("Enregistrer en brouillon", corps)
        self.assertIn("Argent reçu", corps)
        self.assertIn("Argent dépensé", corps)

    def test_les_permissions_suivent_le_role_dans_lentreprise(self):
        self.member.role = MembreOrganisation.Role.LECTURE
        self.member.save(update_fields=["role"])
        self.assertEqual(self.client.get(self.base).status_code, 200)
        self.assertEqual(self.client.get(f"{self.base}nouvelle/").status_code, 403)

        self.member.role = MembreOrganisation.Role.RESPONSABLE
        self.member.save(update_fields=["role"])
        self.assertEqual(self.client.get(f"{self.base}nouvelle/").status_code, 200)

    def test_le_formulaire_sadapte_au_type_choisi(self):
        """Le coeur de l'idee : le formulaire change selon l'operation."""
        transport = self.client.get(
            f"{self.base}nouvelle/?type=CHARGE_TRANSPORT"
        ).content.decode()
        self.assertIn('name="compte_tresorerie"', transport)
        self.assertIn('name="motif"', transport)
        self.assertIn('name="beneficiaire"', transport)
        self.assertNotIn('name="date_echeance"', transport)

        facture = self.client.get(
            f"{self.base}nouvelle/?type=FACTURE_FOURNISSEUR"
        ).content.decode()
        self.assertIn('name="date_echeance"', facture)
        self.assertIn('name="numero_piece"', facture)
        self.assertIn('name="montant_tva"', facture)
        # Une facture n'est pas un paiement : aucun compte de trésorerie.
        self.assertNotIn('name="compte_tresorerie"', facture)
        self.assertNotIn('name="motif"', facture)

        depot = self.client.get(
            f"{self.base}nouvelle/?type=DEPOT_BANQUE"
        ).content.decode()
        self.assertIn('name="compte_tresorerie"', depot)
        self.assertIn('name="compte_destination"', depot)

    def test_aucun_debit_ni_credit_nest_demande(self):
        for type_operation in ("ENCAISSEMENT", "CHARGE_TRANSPORT", "FACTURE_CLIENT"):
            with self.subTest(type=type_operation):
                corps = self.client.get(
                    f"{self.base}nouvelle/?type={type_operation}"
                ).content.decode()
                self.assertNotIn('name="debit"', corps)
                self.assertNotIn('name="credit"', corps)

    def test_creer_en_brouillon_ne_comptabilise_pas(self):
        reponse = self.client.post(
            f"{self.base}nouvelle/",
            {
                "type_operation": "ENCAISSEMENT",
                "date_operation": date.today().isoformat(),
                "description": "Encaissement brouillon",
                "montant": "15000",
                "compte_tresorerie": self.caisse.pk,
                "brouillon": "1",
            },
        )
        self.assertEqual(reponse.status_code, 302)
        operation = Operation.objects.get(description="Encaissement brouillon")
        self.assertEqual(operation.statut, Operation.Statut.BROUILLON)
        self.assertIsNone(operation.ecriture)
        self.assertEqual(operation.organisation_id, self.organisation.pk)
        self.assertTrue(operation.numero)
        self.assertEqual(operation.devise, self.organisation.devise)

    def test_creer_et_valider_genere_lecriture(self):
        self.client.post(
            f"{self.base}nouvelle/",
            {
                "type_operation": "CHARGE_TRANSPORT",
                "date_operation": date.today().isoformat(),
                "description": "Carburant mission",
                "montant": "20000",
                "compte_tresorerie": self.caisse.pk,
                "beneficiaire": "Chauffeur",
                "motif": "Mission Ségou",
                "centre_cout": "Logistique",
                "valider": "1",
            },
        )
        operation = Operation.objects.get(description="Carburant mission")
        self.assertEqual(operation.statut, Operation.Statut.VALIDEE)
        self.assertIsNotNone(operation.ecriture)
        self.assertTrue(operation.ecriture.est_equilibree)
        # Les champs propres au type sont conserves sans migration.
        self.assertEqual(operation.donnees.get("motif"), "Mission Ségou")
        self.assertEqual(operation.centre_cout, "Logistique")
        self.caisse.refresh_from_db()
        self.assertEqual(self.caisse.solde_actuel, Decimal("80000"))
        self.assertIsNotNone(operation.mouvement)

    def test_le_detail_affiche_lecriture_generee(self):
        self.client.post(
            f"{self.base}nouvelle/",
            {
                "type_operation": "ENCAISSEMENT",
                "date_operation": date.today().isoformat(),
                "description": "Vente comptoir",
                "montant": "9000",
                "compte_tresorerie": self.caisse.pk,
                "valider": "1",
            },
        )
        operation = Operation.objects.get(description="Vente comptoir")
        reponse = self.client.get(f"{self.base}{operation.pk}/")
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "Impact financier")
        self.assertNotContains(reponse, "Débit")
        self.assertNotContains(reponse, "Crédit")

    def test_un_montant_negatif_est_refuse(self):
        reponse = self.client.post(
            f"{self.base}nouvelle/",
            {
                "type_operation": "ENCAISSEMENT",
                "date_operation": date.today().isoformat(),
                "description": "Montant invalide",
                "montant": "-5000",
                "compte_tresorerie": self.caisse.pk,
                "valider": "1",
            },
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(Operation.objects.filter(description="Montant invalide").exists())

    def test_un_transfert_sans_destination_est_refuse(self):
        reponse = self.client.post(
            f"{self.base}nouvelle/",
            {
                "type_operation": "TRANSFERT",
                "date_operation": date.today().isoformat(),
                "description": "Transfert incomplet",
                "montant": "5000",
                "compte_tresorerie": self.caisse.pk,
                "valider": "1",
            },
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(
            Operation.objects.filter(description="Transfert incomplet").exists()
        )


class IsolationOperationTest(TestCase):
    """Une organisation ne doit jamais voir les operations d'une autre."""

    @classmethod
    def setUpTestData(cls):
        cls.org_a = creer_organisation("Centre A", "ops-iso-a")
        cls.org_b = creer_organisation("Centre B", "ops-iso-b")

        cls.operation_b = Operation.objects.create(
            organisation=cls.org_b,
            numero="OP-2026-00001",
            date_operation=date.today(),
            type_operation="ENCAISSEMENT",
            description="Operation confidentielle de B",
            montant=Decimal("77000"),
        )

        cls.user_a = get_user_model().objects.create_user(
            username="iso-a", password="test1234"
        )
        MembreOrganisation.objects.create(
            organisation=cls.org_a,
            user=cls.user_a,
            role=MembreOrganisation.Role.ADMIN,
        )

    def setUp(self):
        self.client.force_login(self.user_a)

    def test_la_liste_de_a_ne_montre_pas_les_operations_de_b(self):
        reponse = self.client.get(f"/o/{self.org_a.slug}/operations/")
        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, "Operation confidentielle de B")

    def test_ouvrir_une_operation_de_b_depuis_lespace_de_a_renvoie_404(self):
        """L'identifiant est injecte dans l'espace legitime de A."""
        reponse = self.client.get(
            f"/o/{self.org_a.slug}/operations/{self.operation_b.pk}/"
        )
        self.assertEqual(reponse.status_code, 404)

    def test_valider_une_operation_de_b_depuis_lespace_de_a_renvoie_404(self):
        reponse = self.client.post(
            f"/o/{self.org_a.slug}/operations/{self.operation_b.pk}/valider/"
        )
        self.assertEqual(reponse.status_code, 404)
        self.operation_b.refresh_from_db()
        self.assertEqual(self.operation_b.statut, Operation.Statut.BROUILLON)
