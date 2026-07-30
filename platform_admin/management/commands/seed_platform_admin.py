from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from platform_admin.models import FeatureFlag, PlatformStaffProfile


class Command(BaseCommand):
    help = "Initialise les accès et feature flags de la console SahelTech."

    def handle(self, *args, **options):
        admin_user = get_user_model().objects.filter(
            username="admin",
            is_superuser=True,
        ).first()
        if admin_user:
            PlatformStaffProfile.objects.update_or_create(
                user=admin_user,
                defaults={
                    "role": PlatformStaffProfile.Role.SUPER_ADMIN,
                    "is_active": True,
                },
            )

        flags = [
            ("intelligence-artificielle", "Intelligence artificielle"),
            ("api-publique", "API publique"),
            ("multi-agence", "Multi-agence"),
            ("signature-electronique", "Signature électronique"),
            ("export-excel-avance", "Export Excel avancé"),
        ]
        for code, nom in flags:
            FeatureFlag.objects.get_or_create(
                code=code,
                defaults={"nom": nom, "description": "", "rollout_percentage": 0},
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Console SahelTech initialisée : accès admin et feature flags."
            )
        )
