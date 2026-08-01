"""Le moteur d'operations genere la comptabilite a partir de l'evenement metier.

L'utilisateur declare ce qui s'est passe ; aucun debit ni credit n'est saisi.
Ces tests verifient que l'ecriture produite est correcte, equilibree, rattachee
a la bonne organisation, et qu'elle suit les regles configurables.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from comptabilite_ohada.models import (
    ExerciceComptable,
    RegleComptable,
    TypeOperationComptable,
)
from comptabilite_ohada.services.initialisation_service import InitialisationService
from comptes.models import Compte
from operations.models import Operation
from operations.services import OperationEngine
from organisations.models import Organisation


def creer_organisation(nom, slug):
    return Organisation.objects.create(
        nom=nom,
        slug=slug,
        email=f"{slug}@test.test",
        telephone="+22300000000",
        statut=Organisation.Statut.ACTIVE,
    )


def creer_exercice(organisation):
    annee = date.today().year
    return ExerciceComptable.objects.create(
        code=f"{slugify_code(organisation.slug)}-{annee}",
        date_debut=date(annee, 1, 1),
        date_fin=date(annee, 12, 31),
        organisation=organisation,
    )


def slugify_code(valeur):
    return valeur.upper()[:6]


class MoteurOperationTest(TestCase):
    def setUp(self):
        InitialisationService.charger_plan_comptable()
        InitialisationService.initialiser_journaux()
        self.user = get_user_model().objects.create_superuser(
            username="op-admin", password="test1234"
        )
        self.organisation = creer_organisation("Centre Ops", "centre-ops")
        creer_exercice(self.organisation)
        self.caisse = Compte.objects.create(
            code="CAISSE-OP",
            nom="Caisse principale",
            type="ESPECES",
            solde_actuel=Decimal("0"),
            compte_comptable_code="571",
            organisation=self.organisation,
        )
        self.banque = Compte.objects.create(
            code="BANQUE-OP",
            nom="Compte bancaire",
            type="BANQUE",
            solde_actuel=Decimal("0"),
            compte_comptable_code="521",
            organisation=self.organisation,
        )

    def _operation(self, type_operation, **extra):
        valeurs = {
            "organisation": self.organisation,
            "numero": OperationEngine.numeroter(self.organisation, date.today()),
            "date_operation": date.today(),
            "type_operation": type_operation,
            "description": f"Test {type_operation}",
            "montant": Decimal("25000"),
            "compte_tresorerie": self.caisse,
            "cree_par": self.user,
        }
        valeurs.update(extra)
        return Operation.objects.create(**valeurs)

    # ─── Numerotation ────────────────────────────────────────

    def test_la_numerotation_est_sequentielle_par_organisation(self):
        premier = OperationEngine.numeroter(self.organisation, date.today())
        self._operation("ENCAISSEMENT", numero=premier)
        second = OperationEngine.numeroter(self.organisation, date.today())
        self.assertEqual(premier, f"OP-{date.today().year}-00001")
        self.assertEqual(second, f"OP-{date.today().year}-00002")

    def test_deux_organisations_ont_des_numerotations_independantes(self):
        autre = creer_organisation("Autre Ops", "autre-ops")
        self._operation("ENCAISSEMENT")
        numero_autre = OperationEngine.numeroter(autre, date.today())
        self.assertEqual(numero_autre, f"OP-{date.today().year}-00001")

    # ─── Comptabilisation ────────────────────────────────────

    def test_un_encaissement_genere_une_ecriture_equilibree(self):
        operation = self._operation("ENCAISSEMENT")
        OperationEngine.executer(operation, user=self.user)

        operation.refresh_from_db()
        self.assertEqual(operation.statut, Operation.Statut.VALIDEE)
        self.assertIsNotNone(operation.ecriture)
        self.assertTrue(operation.ecriture.est_equilibree)
        self.assertEqual(operation.ecriture.organisation_id, self.organisation.pk)

        codes = set(operation.ecriture.lignes.values_list("compte__code", flat=True))
        # Le compte de tresorerie vient de l'operation, la contrepartie de la regle.
        self.assertIn("571", codes)
        self.assertIn("706", codes)

    def test_un_decaissement_inverse_le_sens(self):
        operation = self._operation("DECAISSEMENT")
        OperationEngine.executer(operation, user=self.user)
        lignes = {
            ligne.compte.code: ligne
            for ligne in operation.ecriture.lignes.select_related("compte")
        }
        # La charge est debitee, la tresorerie creditee.
        self.assertGreater(lignes["658"].debit, 0)
        self.assertGreater(lignes["571"].credit, 0)

    def test_une_charge_de_transport_utilise_la_regle_de_decaissement(self):
        operation = self._operation(
            "CHARGE_TRANSPORT",
            donnees={"beneficiaire": "Chauffeur", "motif": "Mission Ségou"},
            centre_cout="Logistique",
        )
        OperationEngine.executer(operation, user=self.user)
        self.assertTrue(operation.ecriture.est_equilibree)
        self.assertEqual(operation.centre_cout, "Logistique")

    def test_un_transfert_mouvemente_les_deux_comptes(self):
        operation = self._operation("TRANSFERT", compte_destination=self.banque)
        OperationEngine.executer(operation, user=self.user)
        codes = set(operation.ecriture.lignes.values_list("compte__code", flat=True))
        self.assertEqual(codes, {"571", "521"})

    def test_une_facture_fournisseur_nexige_pas_de_tresorerie(self):
        operation = self._operation(
            "FACTURE_FOURNISSEUR",
            compte_tresorerie=None,
            donnees={"tiers": "Fournisseur X", "numero_piece": "F-001"},
        )
        OperationEngine.executer(operation, user=self.user)
        codes = set(operation.ecriture.lignes.values_list("compte__code", flat=True))
        # Les deux cotes viennent de la regle : charge et dette fournisseur.
        self.assertIn("401", codes)

    # ─── Regles configurables ────────────────────────────────

    def test_une_regle_de_lorganisation_change_les_comptes_generes(self):
        RegleComptable.objects.create(
            organisation=self.organisation,
            type_operation=TypeOperationComptable.ENCAISSEMENT,
            compte_credit="701",
            journal_code="VN",
        )
        operation = self._operation("ENCAISSEMENT")
        OperationEngine.executer(operation, user=self.user)
        codes = set(operation.ecriture.lignes.values_list("compte__code", flat=True))
        self.assertIn("701", codes)
        self.assertNotIn("706", codes)

    # ─── Garde-fous ──────────────────────────────────────────

    def test_un_type_inconnu_est_refuse(self):
        operation = self._operation("TYPE_QUI_NEXISTE_PAS")
        with self.assertRaises(ValidationError):
            OperationEngine.executer(operation, user=self.user)
        operation.refresh_from_db()
        self.assertEqual(operation.statut, Operation.Statut.BROUILLON)

    def test_un_montant_nul_est_refuse(self):
        operation = self._operation("ENCAISSEMENT", montant=Decimal("0"))
        with self.assertRaises(ValidationError):
            OperationEngine.executer(operation, user=self.user)

    def test_un_compte_dune_autre_organisation_est_refuse(self):
        """Un identifiant venu d'un formulaire ne doit pas franchir le tenant."""
        autre = creer_organisation("Voisin", "voisin-ops")
        compte_voisin = Compte.objects.create(
            code="CAISSE-VOISIN",
            nom="Caisse du voisin",
            type="ESPECES",
            solde_actuel=Decimal("0"),
            compte_comptable_code="571",
            organisation=autre,
        )
        operation = self._operation("ENCAISSEMENT", compte_tresorerie=compte_voisin)
        with self.assertRaises(ValidationError):
            OperationEngine.executer(operation, user=self.user)

    def test_un_transfert_vers_le_meme_compte_est_refuse(self):
        operation = self._operation("TRANSFERT", compte_destination=self.caisse)
        with self.assertRaises(ValidationError):
            OperationEngine.executer(operation, user=self.user)

    def test_une_operation_deja_validee_ne_peut_pas_etre_rejouee(self):
        operation = self._operation("ENCAISSEMENT")
        OperationEngine.executer(operation, user=self.user)
        with self.assertRaises(ValidationError):
            OperationEngine.executer(operation, user=self.user)

    def test_une_operation_sans_tresorerie_quand_elle_en_exige_est_refusee(self):
        operation = self._operation("ENCAISSEMENT", compte_tresorerie=None)
        with self.assertRaises(ValidationError):
            OperationEngine.executer(operation, user=self.user)
