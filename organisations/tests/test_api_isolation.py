"""Tests d'isolation des API REST.

Trois regressions sont verrouillees ici :

1. les API comptables etaient accessibles **sans authentification** (aucun
   permission_classes et aucun DEFAULT_PERMISSION_CLASSES : DRF appliquait
   AllowAny, y compris en ecriture) ;
2. les ViewSets ne filtraient pas par organisation, donc un membre de A
   pouvait lire et modifier les donnees de B ;
3. les mouvements de tresorerie acceptaient un compte_id arbitraire, ce qui
   permettait d'encaisser, decaisser ou transferer sur le compte d'un autre
   client.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from comptabilite_ohada.models import (
    EcritureComptable,
    ExerciceComptable,
    JournalComptable,
)
from comptes.models import Compte
from organisations.models import MembreOrganisation, Organisation

API_COMPTA = "/o/{slug}/comptabilite/api/comptabilite"
API_TRESO = "/o/{slug}/api/comptes-financiers"


def build_accounting_tenant(suffix, slug, journal):
    organisation = Organisation.objects.create(
        nom=f"Centre {suffix}",
        slug=slug,
        email=f"{slug}@test.test",
        telephone="+22300000000",
    )
    exercice = ExerciceComptable.objects.create(
        code=f"EX-{suffix}",
        date_debut="2025-01-01",
        date_fin="2025-12-31",
        organisation=organisation,
    )
    ecriture = EcritureComptable.objects.create(
        journal=journal,
        exercice=exercice,
        date_ecriture="2025-06-01",
        reference=f"REF-{suffix}",
        libelle=f"Ecriture {suffix}",
        organisation=organisation,
    )
    compte = Compte.objects.create(
        organisation=organisation,
        code=f"CPT-{suffix}",
        nom=f"Caisse {suffix}",
        type="CAISSE",
        solde_actuel=Decimal("500000"),
    )
    return {
        "organisation": organisation,
        "exercice": exercice,
        "ecriture": ecriture,
        "compte": compte,
    }


class ApiRequiresAuthenticationTest(TestCase):
    """Verrouille la regression d'exposition anonyme."""

    @classmethod
    def setUpTestData(cls):
        cls.journal = JournalComptable.objects.create(
            code="OD", libelle="Operations diverses", type_journal="OD"
        )
        cls.a = build_accounting_tenant("Alpha", "api-alpha", cls.journal)

    def test_les_api_comptables_refusent_lanonyme_en_lecture(self):
        base = API_COMPTA.format(slug="api-alpha")
        for endpoint in (
            "comptes",
            "ecritures",
            "journaux",
            "exercices",
            "configurations",
            "immobilisations",
        ):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(f"{base}/{endpoint}/")
                self.assertIn(response.status_code, (401, 403))

    def test_les_api_comptables_refusent_lanonyme_en_ecriture(self):
        before = JournalComptable.objects.count()
        response = self.client.post(
            f"{API_COMPTA.format(slug='api-alpha')}/journaux/",
            {"code": "PWN", "libelle": "Anonyme", "type_journal": "OD"},
        )
        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(JournalComptable.objects.count(), before)

    def test_lapi_tresorerie_refuse_lanonyme(self):
        response = self.client.get(
            f"{API_TRESO.format(slug='api-alpha')}/comptes/"
        )
        self.assertIn(response.status_code, (401, 403))


class ApiTenantIsolationTest(TestCase):
    """Un membre authentifie de A ne doit pas atteindre les donnees de B."""

    @classmethod
    def setUpTestData(cls):
        cls.journal = JournalComptable.objects.create(
            code="OD", libelle="Operations diverses", type_journal="OD"
        )
        cls.a = build_accounting_tenant("Alpha", "api-alpha", cls.journal)
        cls.b = build_accounting_tenant("Beta", "api-beta", cls.journal)

        cls.user_a = get_user_model().objects.create_user(
            username="api-membre-alpha",
            email="api-membre@alpha.test",
            password="test1234",
        )
        cls.user_a.user_permissions.set(Permission.objects.all())
        MembreOrganisation.objects.create(
            organisation=cls.a["organisation"],
            user=cls.user_a,
            role=MembreOrganisation.Role.ADMIN,
        )

    def setUp(self):
        self.client.force_login(self.user_a)

    def test_la_liste_des_ecritures_ne_montre_que_lorganisation_courante(self):
        response = self.client.get(
            f"{API_COMPTA.format(slug='api-alpha')}/ecritures/"
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("REF-Alpha", body)
        self.assertNotIn("REF-Beta", body)

    def test_ouvrir_une_ecriture_de_b_renvoie_404(self):
        response = self.client.get(
            f"{API_COMPTA.format(slug='api-alpha')}/ecritures/"
            f"{self.b['ecriture'].pk}/"
        )
        self.assertEqual(response.status_code, 404)

    def test_ouvrir_un_exercice_de_b_renvoie_404(self):
        response = self.client.get(
            f"{API_COMPTA.format(slug='api-alpha')}/exercices/"
            f"{self.b['exercice'].pk}/"
        )
        self.assertEqual(response.status_code, 404)

    def test_valider_une_ecriture_de_b_est_refuse(self):
        response = self.client.post(
            f"{API_COMPTA.format(slug='api-alpha')}/ecritures/"
            f"{self.b['ecriture'].pk}/valider/"
        )
        self.assertEqual(response.status_code, 404)
        self.b["ecriture"].refresh_from_db()
        self.assertFalse(self.b["ecriture"].validee)

    def test_un_etat_financier_refuse_un_exercice_de_b(self):
        for endpoint in ("balance", "bilan", "compte_resultat", "grand_livre"):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(
                    f"{API_COMPTA.format(slug='api-alpha')}/ecritures/"
                    f"{endpoint}/",
                    {"exercice": self.b["exercice"].pk},
                )
                self.assertEqual(response.status_code, 404)

    def test_le_plan_comptable_partage_est_en_lecture_seule(self):
        """Le plan SYSCOHADA est commun : un client ne doit pas l'alterer."""
        response = self.client.post(
            f"{API_COMPTA.format(slug='api-alpha')}/comptes/",
            {"code": "999", "libelle": "Injecte", "nature": "DEBIT"},
        )
        self.assertIn(response.status_code, (403, 405))

    def test_la_liste_des_comptes_de_tresorerie_est_isolee(self):
        response = self.client.get(
            f"{API_TRESO.format(slug='api-alpha')}/comptes/"
        )
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("CPT-Alpha", body)
        self.assertNotIn("CPT-Beta", body)

    def test_encaisser_sur_un_compte_de_b_est_refuse(self):
        solde_avant = self.b["compte"].solde_actuel
        response = self.client.post(
            f"{API_TRESO.format(slug='api-alpha')}/mouvements/encaisser/",
            {
                "compte_id": self.b["compte"].pk,
                "montant": "50000",
                "libelle": "Tentative",
            },
        )
        self.assertIn(response.status_code, (400, 403, 404))
        self.b["compte"].refresh_from_db()
        self.assertEqual(self.b["compte"].solde_actuel, solde_avant)

    def test_decaisser_sur_un_compte_de_b_est_refuse(self):
        solde_avant = self.b["compte"].solde_actuel
        response = self.client.post(
            f"{API_TRESO.format(slug='api-alpha')}/mouvements/decaisser/",
            {
                "compte_id": self.b["compte"].pk,
                "montant": "50000",
                "libelle": "Tentative",
            },
        )
        self.assertIn(response.status_code, (400, 403, 404))
        self.b["compte"].refresh_from_db()
        self.assertEqual(self.b["compte"].solde_actuel, solde_avant)

    def test_transferer_depuis_un_compte_de_b_est_refuse(self):
        solde_avant = self.b["compte"].solde_actuel
        response = self.client.post(
            f"{API_TRESO.format(slug='api-alpha')}/transferts/transferer/",
            {
                "source_id": self.b["compte"].pk,
                "destination_id": self.a["compte"].pk,
                "montant": "50000",
            },
        )
        self.assertIn(response.status_code, (400, 403, 404))
        self.b["compte"].refresh_from_db()
        self.assertEqual(self.b["compte"].solde_actuel, solde_avant)

    def test_la_synthese_de_tresorerie_nagrege_pas_les_autres_clients(self):
        response = self.client.get(
            f"{API_TRESO.format(slug='api-alpha')}/comptes/synthese/"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        # Seul le compte de A doit etre compte : sans filtre tenant, la
        # synthese remontait 2 comptes et 1 000 000 de solde cumule.
        self.assertEqual(payload["nb_comptes_actifs"], 1)
        self.assertEqual(Decimal(str(payload["solde_total"])), Decimal("500000"))
