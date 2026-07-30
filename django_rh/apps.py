from django.apps import AppConfig


class RhConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_rh"
    label = "rh"
    verbose_name = "Ressources Humaines"

    def ready(self):
        import django_rh.signals
