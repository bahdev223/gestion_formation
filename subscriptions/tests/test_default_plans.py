from django.core.management import call_command
from django.test import TestCase

from platform_admin.forms import PlatformOrganisationCreateForm
from subscriptions.models import PlanAbonnement
from subscriptions.plan_defaults import ensure_default_plans


class DefaultPlansTest(TestCase):
    def setUp(self):
        PlanAbonnement.objects.all().delete()

    def test_seed_plans_cree_les_trois_offres(self):
        call_command("seed_plans", verbosity=0)

        self.assertEqual(
            set(PlanAbonnement.objects.values_list("code", flat=True)),
            {"STARTER", "PREMIUM", "PRO"},
        )
        self.assertEqual(
            PlanAbonnement.objects.filter(is_active=True).count(),
            3,
        )
        self.assertEqual(
            dict(PlanAbonnement.objects.values_list("code", "nom")),
            {
                "STARTER": "Basic",
                "PREMIUM": "Business",
                "PRO": "Enterprise",
            },
        )
        form = PlatformOrganisationCreateForm()
        self.assertEqual(form.fields["plan"].queryset.count(), 3)

    def test_bootstrap_est_idempotent_et_preserve_les_personnalisations(self):
        plans, _ = ensure_default_plans()
        starter = plans["STARTER"]
        starter.prix_mensuel = 12345
        starter.save(update_fields=["prix_mensuel"])

        ensure_default_plans()

        self.assertEqual(PlanAbonnement.objects.count(), 3)
        starter.refresh_from_db()
        self.assertEqual(starter.prix_mensuel, 12345)
