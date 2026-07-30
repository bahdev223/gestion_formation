from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from organisations.models import MembreOrganisation, Organisation
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
