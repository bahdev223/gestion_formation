from django.apps import AppConfig


class PlatformAdminConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "platform_admin"
    verbose_name = "Administration SahelTech"

    def ready(self):
        from . import signals  # noqa: F401
