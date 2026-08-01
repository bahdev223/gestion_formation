"""Les comptes viennent de RegleComptable, plus du code.

Avant, le pont evenementiel ecrivait « 706 » et « 658 » en dur : adapter le
plan comptable d'un client imposait de modifier le code. Ces tests verifient
que le comportement est inchange sans regle, et qu'une regle propre a une
entreprise change reellement l'ecriture produite.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from comptes.models import Compte
from comptes.services import MouvementCompteService
from organisations.models import Organisation

from ..models import (
    ConfigurationComptable,
    EcritureComptable,
    ExerciceComptable,
    RegleComptable,
    TypeOperationComptable,
)
from ..services.initialisation_service import InitialisationService
from ..services.regle_service import RegleComptableService


def creer_organisation(nom, slug):
    return Organisation.objects.create(
        nom=nom,
        slug=slug,
        email=f"{slug}@test.test",
        telephone="+22300000000",
        statut=Organisation.Statut.ACTIVE,
    )


class ResolutionRegleTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organisation = creer_organisation("Centre Regle", "centre-regle")

    def test_sans_regle_le_defaut_reprend_le_comportement_precedent(self):
        regle = RegleComptableService.resoudre(
            self.organisation, TypeOperationComptable.ENCAISSEMENT
        )
        self.assertEqual(regle["compte_credit"], "706")
        regle = RegleComptableService.resoudre(
            self.organisation, TypeOperationComptable.DECAISSEMENT
        )
        self.assertEqual(regle["compte_debit"], "658")

    def test_une_regle_de_lorganisation_prime_sur_le_defaut(self):
        RegleComptable.objects.create(
            organisation=self.organisation,
            type_operation=TypeOperationComptable.ENCAISSEMENT,
            compte_credit="701",
            journal_code="VN",
        )
        regle = RegleComptableService.resoudre(
            self.organisation, TypeOperationComptable.ENCAISSEMENT
        )
        self.assertEqual(regle["compte_credit"], "701")

    def test_une_regle_desactivee_est_ignoree(self):
        RegleComptable.objects.create(
            organisation=self.organisation,
            type_operation=TypeOperationComptable.ENCAISSEMENT,
            compte_credit="701",
            actif=False,
        )
        regle = RegleComptableService.resoudre(
            self.organisation, TypeOperationComptable.ENCAISSEMENT
        )
        self.assertEqual(regle["compte_credit"], "706")

    def test_la_regle_dune_autre_organisation_ne_fuit_pas(self):
        autre = creer_organisation("Autre", "centre-regle-autre")
        RegleComptable.objects.create(
            organisation=autre,
            type_operation=TypeOperationComptable.ENCAISSEMENT,
            compte_credit="999",
        )
        regle = RegleComptableService.resoudre(
            self.organisation, TypeOperationComptable.ENCAISSEMENT
        )
        self.assertEqual(regle["compte_credit"], "706")

    def test_resoudre_exige_une_organisation(self):
        with self.assertRaises(ValueError):
            RegleComptableService.resoudre(
                None, TypeOperationComptable.ENCAISSEMENT
            )

    def test_le_compte_de_tresorerie_vient_de_la_configuration(self):
        """Le « 571 » litteral ignorait ce reglage, qui existait deja."""
        self.assertEqual(
            RegleComptableService.compte_tresorerie_defaut(self.organisation),
            "571",
        )
        ConfigurationComptable.objects.create(
            organisation=self.organisation, compte_caisse_defaut="572"
        )
        self.assertEqual(
            RegleComptableService.compte_tresorerie_defaut(self.organisation),
            "572",
        )

    def test_initialiser_cree_les_regles_sans_ecraser(self):
        RegleComptable.objects.create(
            organisation=self.organisation,
            type_operation=TypeOperationComptable.ENCAISSEMENT,
            compte_credit="701",
        )
        creees = RegleComptableService.initialiser(self.organisation)
        self.assertGreater(creees, 0)
        personnalisee = RegleComptable.objects.get(
            organisation=self.organisation,
            type_operation=TypeOperationComptable.ENCAISSEMENT,
        )
        self.assertEqual(personnalisee.compte_credit, "701")


class EcritureGenereeParRegleTest(TestCase):
    """Bout en bout : un encaissement doit suivre la regle de l'entreprise."""

    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="regle-admin", password="test1234"
        )
        InitialisationService.charger_plan_comptable()
        InitialisationService.initialiser_journaux()
        self.organisation = creer_organisation("Centre Flux", "centre-flux")
        annee = date.today().year
        ExerciceComptable.objects.create(
            code=str(annee),
            date_debut=date(annee, 1, 1),
            date_fin=date(annee, 12, 31),
            organisation=self.organisation,
        )
        self.caisse = Compte.objects.create(
            code="CAISSE-R",
            nom="Caisse regle",
            type="ESPECES",
            solde_actuel=Decimal("0"),
            compte_comptable_code="571",
            organisation=self.organisation,
        )

    def _encaisser(self):
        MouvementCompteService.encaisser(
            compte=self.caisse,
            montant=Decimal("30000"),
            libelle="Encaissement teste",
            user=self.user,
        )
        return EcritureComptable.objects.get(libelle="Encaissement teste")

    def test_sans_regle_lecriture_utilise_le_compte_par_defaut(self):
        ecriture = self._encaisser()
        codes = set(
            ecriture.lignes.values_list("compte__code", flat=True)
        )
        self.assertIn("706", codes)

    def test_une_regle_change_le_compte_sans_toucher_au_code(self):
        RegleComptable.objects.create(
            organisation=self.organisation,
            type_operation=TypeOperationComptable.ENCAISSEMENT,
            compte_credit="701",
            journal_code="VN",
        )
        ecriture = self._encaisser()
        codes = set(
            ecriture.lignes.values_list("compte__code", flat=True)
        )
        self.assertIn("701", codes)
        self.assertNotIn("706", codes)
        self.assertEqual(ecriture.organisation_id, self.organisation.pk)
