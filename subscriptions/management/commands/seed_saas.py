from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from organisations.models import MembreOrganisation, Organisation
from subscriptions.models import Abonnement, PlanAbonnement
from subscriptions.plan_defaults import ensure_default_plans


class Command(BaseCommand):
    help = "Cree les plans SaaS et l'organisation cliente BALY'S GROUP."

    def handle(self, *args, **options):
        plans, _ = ensure_default_plans(update_existing=True)

        organisation, _ = Organisation.objects.update_or_create(
            slug="balys-group",
            defaults={
                "nom": "BALY'S GROUP",
                "email": "contact@balysgroup.com",
                "telephone": "+223 00 00 00 00",
                "pays": "Mali",
                "devise": "FCFA",
                "statut": Organisation.Statut.ACTIVE,
                "is_active": True,
            },
        )

        now = timezone.now()
        Abonnement.objects.update_or_create(
            organisation=organisation,
            defaults={
                "plan": plans[PlanAbonnement.Code.PRO],
                "cycle": Abonnement.Cycle.MENSUEL,
                "statut": Abonnement.Statut.ACTIF,
                "date_debut": now,
                "date_fin": now + timedelta(days=30),
                "renouvellement_automatique": False,
                "montant": plans[PlanAbonnement.Code.PRO].prix_mensuel,
                "jours_grace": 3,
            },
        )

        User = get_user_model()
        owner = User.objects.filter(username="admin").first()
        if owner:
            MembreOrganisation.objects.update_or_create(
                organisation=organisation,
                user=owner,
                defaults={
                    "role": MembreOrganisation.Role.PROPRIETAIRE,
                    "is_active": True,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Plans SaaS crees et BALY'S GROUP configure comme premiere organisation."
            )
        )
