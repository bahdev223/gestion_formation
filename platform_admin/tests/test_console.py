from datetime import timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from organisations.models import MembreOrganisation, Organisation
from platform_admin.models import (
    BackupRecord,
    MaintenanceWindow,
    PlatformAuditEvent,
    PlatformStaffProfile,
    SaaSInvoice,
)
from subscriptions.models import Abonnement, PaiementAbonnement, PlanAbonnement


class PlatformConsoleAccessTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_superuser(
            username="saheltech-admin",
            email="admin@saheltech.test",
            password="test1234",
        )
        cls.tenant_user = get_user_model().objects.create_user(
            username="tenant-owner",
            email="owner@tenant.test",
            password="test1234",
        )
        cls.organisation = Organisation.objects.create(
            nom="Centre SaaS Test",
            slug="centre-saas-test",
            email="contact@saas.test",
            telephone="+22370000010",
        )
        MembreOrganisation.objects.create(
            organisation=cls.organisation,
            user=cls.tenant_user,
            role=MembreOrganisation.Role.PROPRIETAIRE,
        )
        cls.plan = PlanAbonnement.objects.create(
            code=PlanAbonnement.Code.STARTER,
            nom="Starter test",
            prix_mensuel=Decimal("15000"),
            prix_annuel=Decimal("150000"),
            max_utilisateurs=3,
            max_participants=500,
            max_formations_actives=10,
            max_stockage_mo=1024,
        )
        Abonnement.objects.create(
            organisation=cls.organisation,
            plan=cls.plan,
            cycle=Abonnement.Cycle.MENSUEL,
            statut=Abonnement.Statut.ACTIF,
            date_debut=timezone.now(),
            date_fin=timezone.now() + timedelta(days=30),
            montant=cls.plan.prix_mensuel,
        )

    def test_visiteur_est_redirige_vers_la_connexion(self):
        response = self.client.get("/platform/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_administrateur_entreprise_ne_peut_pas_ouvrir_la_console(self):
        self.client.force_login(self.tenant_user)

        response = self.client.get("/platform/")

        self.assertEqual(response.status_code, 403)

    def test_super_admin_peut_ouvrir_tous_les_modules(self):
        self.client.force_login(self.superuser)
        paths = [
            "/platform/",
            "/platform/organisations/",
            "/platform/abonnements/",
            "/platform/facturation/",
            "/platform/support/",
            "/platform/audit/",
            "/platform/monitoring/",
            "/platform/fonctionnalites/",
            "/platform/maintenance/",
            "/platform/sauvegardes/",
            "/platform/statistiques/",
            "/platform/parametres/",
        ]

        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_super_admin_est_dirige_vers_console_apres_connexion(self):
        response = self.client.post(
            "/accounts/login/",
            {
                "username": "admin@saheltech.test",
                "password": "test1234",
            },
        )

        self.assertRedirects(
            response,
            "/platform/",
            fetch_redirect_response=False,
        )

    def test_console_napparait_pas_dans_le_menu_du_tenant(self):
        self.client.force_login(self.tenant_user)

        response = self.client.get("/o/centre-saas-test/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'href="/platform/')


class PlatformOrganisationActionTest(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="support-agent",
            email="support@saheltech.test",
            password="test1234",
            is_staff=True,
        )
        PlatformStaffProfile.objects.create(
            user=self.staff,
            role=PlatformStaffProfile.Role.SUPPORT,
        )
        self.organisation = Organisation.objects.create(
            nom="Client Action",
            slug="client-action",
            email="action@client.test",
            telephone="+22370000011",
            statut=Organisation.Statut.ACTIVE,
        )
        self.client.force_login(self.staff)

    def test_support_peut_suspendre_une_organisation_et_action_est_auditee(self):
        response = self.client.post(
            f"/platform/organisations/{self.organisation.pk}/action/",
            {"action": "suspend"},
        )

        self.assertEqual(response.status_code, 302)
        self.organisation.refresh_from_db()
        self.assertFalse(self.organisation.is_active)
        self.assertEqual(
            self.organisation.statut,
            Organisation.Statut.SUSPENDUE,
        )
        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                organisation=self.organisation,
                metadata__action="suspend",
            ).exists()
        )


class PlatformMaintenanceTest(TestCase):
    def test_maintenance_peut_bloquer_creation_entreprise(self):
        MaintenanceWindow.objects.create(
            titre="Maintenance inscription",
            message="Mise à jour",
            starts_at=timezone.now() - timedelta(minutes=10),
            ends_at=timezone.now() + timedelta(hours=1),
            statut=MaintenanceWindow.Statut.EN_COURS,
            bloque_inscriptions=True,
        )

        response = self.client.post(
            "/creer-entreprise/",
            {
                "organisation_nom": "Entreprise bloquée",
                "organisation_email": "blocked@example.test",
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(
            Organisation.objects.filter(slug="entreprise-bloquee").exists()
        )


class PlatformOperationsTest(TestCase):
    def setUp(self):
        self.ops = get_user_model().objects.create_user(
            username="ops-agent",
            email="ops@saheltech.test",
            password="test1234",
            is_staff=True,
        )
        PlatformStaffProfile.objects.create(
            user=self.ops,
            role=PlatformStaffProfile.Role.OPS,
        )
        self.organisation = Organisation.objects.create(
            nom="Client Backup",
            slug="client-backup",
            email="backup@client.test",
            telephone="+22370000012",
        )
        self.client.force_login(self.ops)

    def test_sauvegarde_est_reellement_generee(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    "/platform/sauvegardes/",
                    {"organisation_id": self.organisation.pk},
                )

                self.assertEqual(response.status_code, 302)
                backup = BackupRecord.objects.get(
                    organisation=self.organisation
                )
                self.assertEqual(
                    backup.statut,
                    BackupRecord.Statut.REUSSIE,
                )
                self.assertGreater(backup.taille_octets, 0)
                self.assertTrue(backup.fichier.name.endswith(".zip"))

    def test_paiement_valide_genere_une_facture(self):
        plan = PlanAbonnement.objects.create(
            code=PlanAbonnement.Code.STARTER,
            nom="Starter facture",
            prix_mensuel=Decimal("12000"),
            prix_annuel=Decimal("120000"),
            max_utilisateurs=3,
            max_participants=100,
            max_formations_actives=5,
            max_stockage_mo=512,
        )
        abonnement = Abonnement.objects.create(
            organisation=self.organisation,
            plan=plan,
            date_debut=timezone.now(),
            date_fin=timezone.now() + timedelta(days=30),
            montant=plan.prix_mensuel,
        )

        paiement = PaiementAbonnement.objects.create(
            abonnement=abonnement,
            reference="PAY-TEST-INVOICE",
            montant=plan.prix_mensuel,
            mode_paiement="Mobile Money",
            statut=PaiementAbonnement.Statut.VALIDE,
            date_paiement=timezone.now(),
        )

        self.assertTrue(
            SaaSInvoice.objects.filter(
                paiement=paiement,
                statut=SaaSInvoice.Statut.PAYEE,
            ).exists()
        )


class PlatformClientOnboardingTest(TestCase):
    def setUp(self):
        self.ops = get_user_model().objects.create_user(
            username="onboarding-agent",
            email="onboarding@saheltech.test",
            password="test1234",
            is_staff=True,
        )
        PlatformStaffProfile.objects.create(
            user=self.ops,
            role=PlatformStaffProfile.Role.OPS,
        )
        self.plan = PlanAbonnement.objects.create(
            code=PlanAbonnement.Code.PREMIUM,
            nom="Premium onboarding",
            prix_mensuel=Decimal("45000"),
            prix_annuel=Decimal("450000"),
            max_utilisateurs=10,
            max_participants=2000,
            max_formations_actives=50,
            max_stockage_mo=4096,
        )
        self.client.force_login(self.ops)

    def test_ops_cree_entreprise_proprietaire_et_essai(self):
        response = self.client.post(
            "/platform/organisations/creer/",
            {
                "organisation_nom": "Academie Horizon",
                "organisation_email": "contact@horizon.test",
                "organisation_telephone": "+22370000100",
                "ville": "Bamako",
                "pays": "Mali",
                "owner_first_name": "Awa",
                "owner_last_name": "Traore",
                "owner_email": "awa@horizon.test",
                "owner_telephone": "+22370000101",
                "owner_matricule": "HOR-ADMIN",
                "plan": self.plan.pk,
                "cycle": Abonnement.Cycle.MENSUEL,
                "activation": "ESSAI",
                "jours_essai": 21,
            },
        )

        self.assertEqual(response.status_code, 200)
        organisation = Organisation.objects.get(slug="academie-horizon")
        owner = organisation.membres.get(
            role=MembreOrganisation.Role.PROPRIETAIRE
        ).user
        self.assertTrue(owner.must_change_password)
        self.assertEqual(owner.username, "HOR-ADMIN")
        self.assertEqual(organisation.abonnement.statut, Abonnement.Statut.ESSAI)
        self.assertContains(response, "Mot de passe temporaire")
        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                organisation=organisation,
                type_evenement=PlatformAuditEvent.Type.ORGANISATION_CREATED,
            ).exists()
        )


class PlatformManualPaymentTest(TestCase):
    def setUp(self):
        self.finance = get_user_model().objects.create_user(
            username="finance-agent",
            email="finance@saheltech.test",
            password="test1234",
            is_staff=True,
        )
        PlatformStaffProfile.objects.create(
            user=self.finance,
            role=PlatformStaffProfile.Role.FINANCE,
        )
        self.organisation = Organisation.objects.create(
            nom="Client Renouvellement",
            slug="client-renouvellement",
            email="client@renew.test",
            telephone="+22370000110",
            statut=Organisation.Statut.ESSAI,
        )
        self.plan = PlanAbonnement.objects.create(
            code=PlanAbonnement.Code.PRO,
            nom="Pro renouvellement",
            prix_mensuel=Decimal("95000"),
            prix_annuel=Decimal("950000"),
            max_utilisateurs=30,
            max_participants=10000,
            max_formations_actives=200,
            max_stockage_mo=10240,
        )
        self.abonnement = Abonnement.objects.create(
            organisation=self.organisation,
            plan=self.plan,
            cycle=Abonnement.Cycle.MENSUEL,
            statut=Abonnement.Statut.ESSAI,
            date_debut=timezone.now(),
            date_fin=timezone.now() + timedelta(days=2),
            montant=self.plan.prix_mensuel,
        )
        self.client.force_login(self.finance)

    def test_finance_enregistre_paiement_et_renouvelle(self):
        old_end = self.abonnement.date_fin
        response = self.client.post(
            f"/platform/organisations/{self.organisation.pk}/paiement/",
            {
                "plan": self.plan.pk,
                "cycle": Abonnement.Cycle.MENSUEL,
                "montant": "95000",
                "mode_paiement": "ESPECES",
                "date_paiement": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "reference": "B2B-CASH-001",
                "notes": "Paiement remis au bureau.",
            },
        )

        self.assertRedirects(
            response,
            f"/platform/organisations/{self.organisation.pk}/",
            fetch_redirect_response=False,
        )
        self.abonnement.refresh_from_db()
        self.organisation.refresh_from_db()
        payment = PaiementAbonnement.objects.get(reference="B2B-CASH-001")
        self.assertEqual(self.abonnement.statut, Abonnement.Statut.ACTIF)
        self.assertGreater(self.abonnement.date_fin, old_end)
        self.assertEqual(self.organisation.statut, Organisation.Statut.ACTIVE)
        self.assertEqual(payment.statut, PaiementAbonnement.Statut.VALIDE)
        self.assertTrue(
            SaaSInvoice.objects.filter(
                paiement=payment,
                statut=SaaSInvoice.Statut.PAYEE,
            ).exists()
        )
