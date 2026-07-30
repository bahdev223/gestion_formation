from django.core.management.base import BaseCommand

from subscriptions.plan_defaults import ensure_default_plans


class Command(BaseCommand):
    help = "Cree les plans Formix manquants sans modifier les plans existants."

    def handle(self, *args, **options):
        plans, created_codes = ensure_default_plans()
        if created_codes:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Plans Formix crees : {', '.join(created_codes)}."
                )
            )
            return
        self.stdout.write(
            self.style.SUCCESS(
                f"Plans Formix deja configures : {', '.join(plans)}."
            )
        )
