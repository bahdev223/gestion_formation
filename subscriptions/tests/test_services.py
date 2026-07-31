from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from organisations.models import MembreOrganisation, Organisation
from participants.models import Participant
from platform_admin.models import PlatformAuditEvent
from subscriptions.models import Abonnement, PlanAbonnement
from subscriptions.services import FeatureService, QuotaService


class SubscriptionServicesTest(TestCase):
    def setUp(self):
        self.organisation = Organisation.objects.create(
            nom="Centre Alpha",
            email="contact@alpha.test",
            telephone="+22300000000",
        )
        self.plan = PlanAbonnement.objects.create(
            code=PlanAbonnement.Code.STARTER,
            nom="Starter",
            prix_mensuel=Decimal("15000"),
            prix_annuel=Decimal("150000"),
            max_utilisateurs=1,
            max_participants=500,
            max_formations_actives=10,
            max_stockage_mo=1024,
            fonctionnalites={"receipts_pdf": True, "advanced_exports": False},
        )
        self.abonnement = Abonnement.objects.create(
            organisation=self.organisation,
            plan=self.plan,
            statut=Abonnement.Statut.ACTIF,
            cycle=Abonnement.Cycle.MENSUEL,
            date_debut=timezone.now(),
            date_fin=timezone.now() + timedelta(days=30),
            montant=self.plan.prix_mensuel,
        )

    def test_feature_service_lit_le_plan_actif(self):
        self.assertTrue(
            FeatureService.has_feature(self.organisation, "receipts_pdf")
        )
        self.assertFalse(
            FeatureService.has_feature(self.organisation, "advanced_exports")
        )

    def test_quota_user_bloque_quand_limite_atteinte(self):
        owner = get_user_model().objects.create_user(username="owner")
        MembreOrganisation.objects.create(
            organisation=self.organisation,
            user=owner,
            role=MembreOrganisation.Role.PROPRIETAIRE,
        )

        self.assertFalse(QuotaService.can_add_user(self.organisation))

    def test_quota_stockage_prend_en_compte_les_fichiers(self):
        from unittest.mock import patch

        with patch.object(
            QuotaService,
            "storage_bytes",
            return_value=(1024 * 1024 * 1024) - 100,
        ):
            self.assertTrue(
                QuotaService.can_store_bytes(self.organisation, 100)
            )
            self.assertFalse(
                QuotaService.can_store_bytes(self.organisation, 101)
            )

    def test_quota_participant_est_bloquant(self):
        self.plan.max_participants = 1
        self.plan.save(update_fields=["max_participants"])
        Participant.objects.create(
            organisation=self.organisation,
            nom="Diallo",
            prenom="Awa",
            telephone="+22370000001",
        )

        with self.assertRaises(ValidationError):
            QuotaService.require_participant_slot(self.organisation)

    def test_quota_formation_active_est_bloquant(self):
        from formations.models import CategorieFormation, Formation

        self.plan.max_formations_actives = 1
        self.plan.save(update_fields=["max_formations_actives"])
        categorie = CategorieFormation.objects.create(
            organisation=self.organisation,
            nom="Management",
        )
        Formation.objects.create(
            organisation=self.organisation,
            categorie=categorie,
            nom="Management operationnel",
            duree=2,
            prix_standard=100000,
            statut=Formation.Statut.ACTIVE,
        )

        with self.assertRaises(ValidationError):
            QuotaService.require_active_formation_slot(self.organisation)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        PUBLIC_APP_URL="https://formix.saheltech.tech",
    )
    def test_alerte_echeance_est_envoyee_une_seule_fois(self):
        owner = get_user_model().objects.create_user(
            username="owner-alert",
            email="owner-alert@example.test",
        )
        MembreOrganisation.objects.create(
            organisation=self.organisation,
            user=owner,
            role=MembreOrganisation.Role.PROPRIETAIRE,
        )
        self.abonnement.date_fin = timezone.now() + timedelta(days=3)
        self.abonnement.save(update_fields=["date_fin", "updated_at"])

        call_command("notify_expiring_subscriptions")
        call_command("notify_expiring_subscriptions")

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                organisation=self.organisation,
                objet_type="SubscriptionExpiryAlert",
            ).exists()
        )
