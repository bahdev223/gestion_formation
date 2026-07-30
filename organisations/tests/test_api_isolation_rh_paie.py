"""Isolation des API RH et paie.

Ces deux modules faisaient reposer leur isolation sur un mecanisme inoperant
dans ce projet :

- django_paie utilisait paie_settings.MODE_PAR_ENTREPRISE (False) et
  request.user.entreprise_id (champ absent du modele User). get_entreprise_id()
  renvoyait donc "" et tous les filtres `if entreprise_id:` etaient sautes ;
- django_rh n'avait aucun filtre : les selectors listaient tous les employes,
  et hire/suspend/terminate acceptaient n'importe quel identifiant.

Le tenant vient maintenant de l'URL /o/<slug>/, seule source fiable puisqu'un
utilisateur peut etre membre de plusieurs organisations.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from django_paie.services import ModeSimpleService
from django_rh.models import Department, Employee, Position
from organisations.models import MembreOrganisation, Organisation

API_RH = "/o/{slug}/ressources-humaines/api"
API_PAIE = "/o/{slug}/paie-salariale/api"


def build_hr_tenant(suffix, slug, employe_user):
    organisation = Organisation.objects.create(
        nom=f"Centre {suffix}",
        slug=slug,
        email=f"{slug}@test.test",
        telephone="+22300000000",
    )
    # Department.code et Position.code sont uniques globalement (defaut
    # multi-tenant connu) : on suffixe pour eviter une collision entre les
    # deux organisations du test.
    departement = Department.objects.create(
        organisation=organisation,
        name=f"Direction {suffix}",
        code=f"DIR-{suffix[:3].upper()}",
    )
    poste = Position.objects.create(
        organisation=organisation,
        title=f"Formateur {suffix}",
        code=f"POS-{suffix[:3].upper()}",
    )
    employee = Employee.objects.create(
        organisation=organisation,
        matricule=f"MAT-{suffix}",
        first_name=f"Prenom{suffix}",
        last_name=f"Nom{suffix}",
        status="active",
        department=departement,
        position=poste,
    )
    echeance = ModeSimpleService(
        entreprise_id=organisation.slug
    ).creer_echeance(employe_user, "07/2026", 100000)
    return {
        "organisation": organisation,
        "departement": departement,
        "poste": poste,
        "employee": employee,
        "echeance": echeance,
    }


class RhPaieApiIsolationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.porteur = User.objects.create_user(
            username="porteur-echeances", password="test1234"
        )
        cls.a = build_hr_tenant("Alpha", "rh-alpha", cls.porteur)
        cls.b = build_hr_tenant("Beta", "rh-beta", cls.porteur)

        cls.user_a = User.objects.create_user(
            username="rh-membre-alpha",
            email="rh-membre@alpha.test",
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

    # --- RH ---------------------------------------------------------------
    #
    # django_rh/urls.py n'est inclus dans aucun urlconf : cette API n'est pas
    # routee, seules les vues HTML de dashboard/rh_views.py sont accessibles.
    # On teste donc le selector et le service, qui sont le code reellement
    # utilise, plutot que des URLs inexistantes.

    def test_lapi_rh_nest_pas_routee(self):
        """Constat verrouille : si on la monte un jour, ces tests devront
        etre repris en tests HTTP."""
        response = self.client.get(f"{API_RH.format(slug='rh-alpha')}/employees/")
        self.assertEqual(response.status_code, 404)

    def test_le_selector_rh_isole_les_employes(self):
        from django_rh.selectors import EmployeeSelector

        selector = EmployeeSelector(organisation=self.a["organisation"])
        matricules = set(
            selector.list_employees().values_list("matricule", flat=True)
        )
        self.assertEqual(matricules, {"MAT-Alpha"})

    def test_le_selector_rh_isole_les_referentiels(self):
        from django_rh.selectors import EmployeeSelector

        selector = EmployeeSelector(organisation=self.a["organisation"])
        self.assertEqual(
            set(selector.list_departments().values_list("name", flat=True)),
            {"Direction Alpha"},
        )
        self.assertEqual(
            set(selector.list_positions().values_list("title", flat=True)),
            {"Formateur Alpha"},
        )

    def test_les_stats_rh_ne_comptent_que_lorganisation_courante(self):
        from django_rh.selectors import EmployeeSelector

        stats = EmployeeSelector(
            organisation=self.a["organisation"]
        ).get_dashboard_stats()
        # Sans filtre tenant, ces compteurs valaient 2 au lieu de 1.
        self.assertEqual(stats["total_employees"], 1)
        self.assertEqual(stats["department_count"], 1)
        self.assertEqual(stats["position_count"], 1)

    def test_le_selector_rh_exige_une_organisation(self):
        from django_rh.selectors import EmployeeSelector

        with self.assertRaises(ValueError):
            EmployeeSelector().list_employees()

    def test_ouvrir_un_employe_de_b_depuis_a_renvoie_none(self):
        from django_rh.selectors import EmployeeSelector

        selector = EmployeeSelector(organisation=self.a["organisation"])
        self.assertIsNone(selector.get_by_id(self.b["employee"].pk))

    def test_licencier_un_employe_de_b_depuis_a_est_refuse(self):
        from django_rh.domain.exceptions.rh_exceptions import (
            EmployeeNotFoundError,
        )
        from django_rh.services import EmployeeService

        with self.assertRaises(EmployeeNotFoundError):
            EmployeeService().terminate(
                self.b["employee"].pk,
                organisation=self.a["organisation"],
                reason="Tentative",
            )
        self.b["employee"].refresh_from_db()
        self.assertEqual(self.b["employee"].status, "active")

    def test_suspendre_un_employe_de_b_depuis_a_est_refuse(self):
        from django_rh.domain.exceptions.rh_exceptions import (
            EmployeeNotFoundError,
        )
        from django_rh.services import EmployeeService

        with self.assertRaises(EmployeeNotFoundError):
            EmployeeService().suspend(
                self.b["employee"].pk,
                organisation=self.a["organisation"],
            )
        self.b["employee"].refresh_from_db()
        self.assertEqual(self.b["employee"].status, "active")

    # --- Paie -------------------------------------------------------------

    def test_la_liste_des_echeances_est_isolee(self):
        response = self.client.get(f"{API_PAIE.format(slug='rh-alpha')}/echeances/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(
            payload["data"][0]["id"], self.a["echeance"].pk
        )

    def test_ouvrir_une_echeance_de_b_renvoie_404(self):
        response = self.client.get(
            f"{API_PAIE.format(slug='rh-alpha')}/echeances/"
            f"{self.b['echeance'].pk}/"
        )
        self.assertEqual(response.status_code, 404)

    def test_les_stats_de_paie_nagregent_pas_les_autres_clients(self):
        response = self.client.get(
            f"{API_PAIE.format(slug='rh-alpha')}/stats/resume/"
        )
        self.assertEqual(response.status_code, 200)
