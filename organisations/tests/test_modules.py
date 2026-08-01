"""Activation des modules selon le plan d'abonnement.

Avant ce dispositif, le menu comportait 19 entrees codees en dur et aucune
condition : un client STARTER voyait Paie salariale, Ressources humaines,
Comptabilite OHADA et Comptes financiers, et pouvait y acceder, alors que son
plan ne les inclut pas. FeatureService existait mais n'etait appele nulle part.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone

from organisations.models import MembreOrganisation, Organisation
from subscriptions.models import Abonnement, PlanAbonnement

# Chemins avec slash final : sans lui, APPEND_SLASH renvoie un 301 et le test
# porterait sur la redirection plutot que sur la vue reelle.
MODULES_GESTION = {
    "paie-salariale/dashboard/": "Paie salariale",
    "ressources-humaines/dashboard/": "Ressources humaines",
    "comptabilite/": "Comptabilité OHADA",
    "comptes-financiers/": "Comptes financiers",
}


def creer_plan(code, **fonctionnalites):
    base = {
        "formations": True,
        "sessions": True,
        "participants": True,
        "inscriptions": True,
        "participant_payments": True,
        "presences": True,
        "simple_attestations": True,
        "hr": False,
        "payroll": False,
        "accounting": False,
        "treasury": False,
    }
    base.update(fonctionnalites)
    return PlanAbonnement.objects.create(
        code=code,
        nom=f"Plan {code}",
        prix_mensuel=Decimal("10000"),
        prix_annuel=Decimal("100000"),
        max_utilisateurs=5,
        max_participants=100,
        max_formations_actives=10,
        max_stockage_mo=512,
        fonctionnalites=base,
    )


def creer_organisation_abonnee(slug, plan):
    organisation = Organisation.objects.create(
        nom=f"Centre {slug}",
        slug=slug,
        email=f"{slug}@test.test",
        telephone="+22300000000",
        statut=Organisation.Statut.ACTIVE,
    )
    now = timezone.now()
    Abonnement.objects.create(
        organisation=organisation,
        plan=plan,
        statut=Abonnement.Statut.ACTIF,
        date_debut=now - timedelta(days=1),
        date_fin=now + timedelta(days=30),
        montant=plan.prix_mensuel,
    )
    return organisation


def rattacher(user, organisation):
    MembreOrganisation.objects.create(
        organisation=organisation,
        user=user,
        role=MembreOrganisation.Role.ADMIN,
    )


class PlanStarterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.plan = creer_plan(PlanAbonnement.Code.STARTER)
        cls.organisation = creer_organisation_abonnee("mod-starter", cls.plan)
        cls.user = get_user_model().objects.create_user(
            username="starter-admin", password="test1234"
        )
        cls.user.user_permissions.set(Permission.objects.all())
        rattacher(cls.user, cls.organisation)

    def setUp(self):
        self.client.force_login(self.user)

    def test_le_menu_masque_les_modules_hors_plan(self):
        response = self.client.get("/o/mod-starter/dashboard/")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        for libelle in MODULES_GESTION.values():
            with self.subTest(libelle=libelle):
                self.assertNotIn(libelle, body)

    def test_len_tete_de_section_disparait_si_tout_est_inactif(self):
        response = self.client.get("/o/mod-starter/dashboard/")
        self.assertNotIn("Gestion de l", response.content.decode())

    def test_les_modules_du_plan_restent_visibles(self):
        response = self.client.get("/o/mod-starter/dashboard/")
        body = response.content.decode()
        for libelle in ("Formations", "Apprenants", "Inscriptions", "Paiements"):
            with self.subTest(libelle=libelle):
                self.assertIn(libelle, body)

    def test_lurl_dun_module_hors_plan_est_refusee(self):
        """Masquer le menu ne suffit pas : l'URL doit aussi etre fermee."""
        for chemin in MODULES_GESTION:
            with self.subTest(chemin=chemin):
                response = self.client.get(f"/o/mod-starter/{chemin}")
                self.assertIn(response.status_code, (403, 404))

    def test_lapi_dun_module_hors_plan_est_refusee(self):
        response = self.client.get(
            "/o/mod-starter/api/comptes-financiers/comptes/"
        )
        self.assertIn(response.status_code, (403, 404))

    def test_les_modules_du_plan_restent_accessibles(self):
        for chemin in ("formations/", "participants/", "inscriptions/"):
            with self.subTest(chemin=chemin):
                response = self.client.get(f"/o/mod-starter/{chemin}")
                self.assertEqual(response.status_code, 200)


class PlanProTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.plan = creer_plan(
            PlanAbonnement.Code.PRO,
            hr=True,
            payroll=True,
            accounting=True,
            treasury=True,
        )
        cls.organisation = creer_organisation_abonnee("mod-pro", cls.plan)
        cls.user = get_user_model().objects.create_user(
            username="pro-admin", password="test1234"
        )
        cls.user.user_permissions.set(Permission.objects.all())
        rattacher(cls.user, cls.organisation)

    def setUp(self):
        self.client.force_login(self.user)

    def test_le_menu_affiche_tous_les_modules(self):
        response = self.client.get("/o/mod-pro/dashboard/")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        for libelle in MODULES_GESTION.values():
            with self.subTest(libelle=libelle):
                self.assertIn(libelle, body)
        self.assertNotIn("dashboard:rh-dashboard", body)
        self.assertNotIn("dashboard:organisation-settings", body)
        self.assertIn('/o/mod-pro/ressources-humaines/dashboard/', body)
        self.assertIn('/o/mod-pro/paie-salariale/dashboard/', body)

    def test_les_modules_de_gestion_sont_accessibles(self):
        for chemin in ("comptabilite/", "comptes-financiers/"):
            with self.subTest(chemin=chemin):
                response = self.client.get(f"/o/mod-pro/{chemin}")
                self.assertEqual(response.status_code, 200)


class FeatureFlagCibleTest(TestCase):
    """Un flag plateforme doit pouvoir ouvrir un module hors plan.

    C'est le mecanisme des modules prives : activation ciblee sur une seule
    organisation, sans changer son abonnement.
    """

    @classmethod
    def setUpTestData(cls):
        cls.plan = creer_plan(PlanAbonnement.Code.STARTER)
        cls.organisation = creer_organisation_abonnee("mod-flag", cls.plan)
        cls.user = get_user_model().objects.create_user(
            username="flag-admin", password="test1234"
        )
        cls.user.user_permissions.set(Permission.objects.all())
        rattacher(cls.user, cls.organisation)

    def setUp(self):
        self.client.force_login(self.user)

    def test_sans_flag_le_module_est_ferme(self):
        response = self.client.get("/o/mod-flag/comptabilite/")
        self.assertIn(response.status_code, (403, 404))

    def test_un_flag_cible_ouvre_le_module_sans_changer_le_plan(self):
        from platform_admin.models import FeatureFlag

        flag = FeatureFlag.objects.create(
            code="accounting", nom="Comptabilité", is_enabled_globally=False
        )
        flag.organisations.add(self.organisation)

        response = self.client.get("/o/mod-flag/comptabilite/")
        self.assertEqual(response.status_code, 200)
        # Le plan n'a pas change.
        self.assertFalse(self.plan.fonctionnalites["accounting"])


class ModuleSansAbonnementTest(TestCase):
    """Une organisation sans abonnement actif ne doit garder que le socle."""

    @classmethod
    def setUpTestData(cls):
        cls.organisation = Organisation.objects.create(
            nom="Centre Sans Abo",
            slug="mod-sans-abo",
            email="sansabo@test.test",
            telephone="+22300000000",
        )
        cls.user = get_user_model().objects.create_user(
            username="sansabo-admin", password="test1234"
        )
        cls.user.user_permissions.set(Permission.objects.all())
        rattacher(cls.user, cls.organisation)

    def test_le_socle_reste_ouvert_et_les_options_fermees(self):
        from core.features import MODULES_DE_BASE, modules_actifs

        actifs = modules_actifs(self.organisation)
        # Le coeur du produit reste accessible : sans cela, une organisation en
        # periode d'essai serait enfermee dehors.
        self.assertEqual(actifs, set(MODULES_DE_BASE))
        for optionnel in ("rh", "paie", "comptabilite", "tresorerie", "api"):
            with self.subTest(module=optionnel):
                self.assertNotIn(optionnel, actifs)

    def test_les_modules_de_base_restent_accessibles_sans_abonnement(self):
        self.client.force_login(self.user)
        for chemin in ("formations/", "participants/", "inscriptions/"):
            with self.subTest(chemin=chemin):
                response = self.client.get(f"/o/mod-sans-abo/{chemin}")
                self.assertEqual(response.status_code, 200)
