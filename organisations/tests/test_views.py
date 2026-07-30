from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from organisations.models import MembreOrganisation, Organisation
from subscriptions.models import Abonnement, PlanAbonnement


class OrganisationDashboardViewTest(TestCase):
    def test_membre_peut_ouvrir_dashboard_organisation(self):
        user = get_user_model().objects.create_user(
            username="owner",
            password="test123",
        )
        organisation = Organisation.objects.create(
            nom="Centre Alpha",
            slug="centre-alpha",
            email="contact@alpha.test",
            telephone="+22300000000",
        )
        MembreOrganisation.objects.create(
            organisation=organisation,
            user=user,
            role=MembreOrganisation.Role.PROPRIETAIRE,
        )
        plan = PlanAbonnement.objects.create(
            code=PlanAbonnement.Code.STARTER,
            nom="Starter",
            prix_mensuel=Decimal("15000"),
            prix_annuel=Decimal("150000"),
            max_utilisateurs=3,
            max_participants=500,
            max_formations_actives=10,
            max_stockage_mo=1024,
        )
        Abonnement.objects.create(
            organisation=organisation,
            plan=plan,
            statut=Abonnement.Statut.ACTIF,
            cycle=Abonnement.Cycle.MENSUEL,
            date_debut=timezone.now(),
            date_fin=timezone.now() + timedelta(days=30),
            montant=plan.prix_mensuel,
        )

        self.client.force_login(user)
        response = self.client.get(
            reverse(
                "organisations:owner-dashboard",
                kwargs={"organisation_slug": organisation.slug},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Centre Alpha")
        self.assertEqual(response.wsgi_request.organisation, organisation)
