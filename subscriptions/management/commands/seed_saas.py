from django.core.management.base import BaseCommand

from subscriptions.plan_defaults import ensure_default_plans


class Command(BaseCommand):
    help = "Crée ou met à jour les plans SaaS par défaut."

    def handle(self, *args, **options):
        plans, _ = ensure_default_plans(update_existing=True)
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(plans)} plans SaaS créés ou mis à jour."
            )
        )
