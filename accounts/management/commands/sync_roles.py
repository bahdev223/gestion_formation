from django.core.management.base import BaseCommand

from accounts.roles import sync_role_groups


class Command(BaseCommand):
    help = "Crée et synchronise les groupes et permissions de la plateforme."

    def handle(self, *args, **options):
        groups = sync_role_groups()
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(groups)} groupes de rôles synchronisés."
            )
        )
