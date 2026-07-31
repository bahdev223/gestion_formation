"""Le moteur comptable rattache l'ecriture a la bonne organisation.

get_exercice() selectionnait le premier exercice ouvert couvrant la date, sans
filtrer par tenant, et creer_ecriture en deduisait l'organisation
(organisation=exercice.organisation). L'ecriture d'un client pouvait donc etre
enregistree dans les livres d'un autre : pas une fuite en lecture, mais une
ecriture dans la comptabilite de la mauvaise entreprise.
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from comptabilite_ohada.models import EcritureComptable, ExerciceComptable
from comptabilite_ohada.services.ecriture_service import EcritureService
from comptabilite_ohada.services.initialisation_service import InitialisationService
from organisations.models import Organisation


def creer_organisation(nom, slug):
    return Organisation.objects.create(
        nom=nom,
        slug=slug,
        email=f"{slug}@test.test",
        telephone="+22300000000",
        statut=Organisation.Statut.ACTIVE,
    )


class ExerciceTenantTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        InitialisationService.charger_plan_comptable()
        InitialisationService.initialiser_journaux()

        cls.org_a = creer_organisation("Centre A", "exo-a")
        cls.org_b = creer_organisation("Centre B", "exo-b")

        annee = date.today().year
        # A est creee en premier : son exercice etait donc celui que
        # get_exercice() renvoyait a tout le monde.
        cls.exercice_a = ExerciceComptable.objects.create(
            code=f"A-{annee}",
            date_debut=date(annee, 1, 1),
            date_fin=date(annee, 12, 31),
            organisation=cls.org_a,
        )
        cls.exercice_b = ExerciceComptable.objects.create(
            code=f"B-{annee}",
            date_debut=date(annee, 1, 1),
            date_fin=date(annee, 12, 31),
            organisation=cls.org_b,
        )

    def _lignes(self):
        return [
            {"compte": EcritureService.get_compte("571"), "debit": Decimal("50000")},
            {"compte": EcritureService.get_compte("706"), "credit": Decimal("50000")},
        ]

    def _journal(self):
        return EcritureService.get_or_create_journal("VE", "Ventes", "VENTES")

    def test_get_exercice_rend_lexercice_de_lorganisation_demandee(self):
        self.assertEqual(
            EcritureService.get_exercice(self.org_a, date.today()).pk,
            self.exercice_a.pk,
        )
        self.assertEqual(
            EcritureService.get_exercice(self.org_b, date.today()).pk,
            self.exercice_b.pk,
        )

    def test_get_exercice_exige_une_organisation(self):
        with self.assertRaises(ValidationError):
            EcritureService.get_exercice(None, date.today())

    def test_lecriture_de_b_est_enregistree_chez_b(self):
        """Le defaut corrige : elle atterrissait dans les livres de A."""
        EcritureService.creer_ecriture(
            reference="VTE-B-001",
            date_ecriture=date.today(),
            libelle="Vente realisee par le Centre B",
            journal=self._journal(),
            lignes=self._lignes(),
            organisation=self.org_b,
        )

        ecriture = EcritureComptable.objects.get(reference="VTE-B-001")
        self.assertEqual(ecriture.organisation_id, self.org_b.pk)
        self.assertEqual(ecriture.exercice_id, self.exercice_b.pk)
        self.assertEqual(
            EcritureComptable.objects.filter(organisation=self.org_a).count(), 0
        )

    def test_creer_ecriture_sans_organisation_est_refuse(self):
        with self.assertRaises(ValidationError):
            EcritureService.creer_ecriture(
                reference="VTE-SANS-ORG",
                date_ecriture=date.today(),
                libelle="Sans tenant",
                journal=self._journal(),
                lignes=self._lignes(),
            )
        self.assertFalse(
            EcritureComptable.objects.filter(reference="VTE-SANS-ORG").exists()
        )

    def test_un_exercice_dune_autre_organisation_est_refuse(self):
        """Garde-fou si les deux arguments sont fournis et se contredisent."""
        with self.assertRaises(ValidationError):
            EcritureService.creer_ecriture(
                reference="VTE-INCOHERENTE",
                date_ecriture=date.today(),
                libelle="Exercice de A pour une operation de B",
                journal=self._journal(),
                lignes=self._lignes(),
                exercice=self.exercice_a,
                organisation=self.org_b,
            )
        self.assertFalse(
            EcritureComptable.objects.filter(reference="VTE-INCOHERENTE").exists()
        )

    def test_les_methodes_metier_exigent_lorganisation(self):
        """organisation est keyword-only et sans defaut sur les 13 methodes."""
        with self.assertRaises(TypeError):
            EcritureService.creer_ecriture_vente(
                compte_caisse_code="571",
                montant=Decimal("1000"),
                libelle="Sans tenant",
                compte_produit_code="706",
            )

    def test_une_vente_passe_par_lexercice_du_bon_tenant(self):
        EcritureService.creer_ecriture_vente(
            compte_caisse_code="571",
            montant=Decimal("25000"),
            libelle="Vente Centre B",
            compte_produit_code="706",
            organisation=self.org_b,
        )
        ecriture = EcritureComptable.objects.get(libelle="Vente Centre B")
        self.assertEqual(ecriture.organisation_id, self.org_b.pk)
        self.assertEqual(ecriture.exercice_id, self.exercice_b.pk)
