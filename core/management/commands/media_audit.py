from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import models
from django.apps import apps


class Command(BaseCommand):
    help = "Audite les champs fichiers/images référencés en base et signale ceux dont le fichier manque."

    def add_arguments(self, parser):
        parser.add_argument(
            "--repair",
            action="store_true",
            help="Réinitialise les champs manquants (None) pour éviter les 404.",
        )
        parser.add_argument(
            "--model",
            action="append",
            default=[],
            help="Limiter l'audit à ces modèles (format app.Model, ex: organisations.Organisation).",
        )

    def _should_scan_model(self, model, requested_models):
        if not requested_models:
            return True
        fullname = f"{model._meta.app_label}.{model.__name__}"
        return fullname in requested_models

    def handle(self, *args, **options):
        requested_models = set(options["model"])
        storage = default_storage

        issues = []
        for model in apps.get_models():
            if not self._should_scan_model(model, requested_models):
                continue
            file_fields = [
                field
                for field in model._meta.fields
                if isinstance(field, (models.ImageField, models.FileField))
            ]
            if not file_fields:
                continue
            for field in file_fields:
                queryset = model._default_manager.only("pk", field.name).iterator()
                for obj in queryset:
                    file_field = getattr(obj, field.name)
                    if not file_field:
                        continue
                    file_path = file_field.name
                    if not file_path:
                        continue
                    if file_path.startswith(storage.base_url or ""):
                        file_path = file_path[len(storage.base_url) :].lstrip("/")
                    try:
                        field_storage = getattr(file_field, "storage", None) or storage
                    except Exception:
                        field_storage = storage

                    if not field_storage.exists(file_path):
                        issues.append(
                            (
                                model._meta.label,
                                obj.pk,
                                field.name,
                                file_path,
                            )
                        )
                        if options["repair"]:
                            setattr(obj, field.name, None)
                            obj.save(update_fields=[field.name])

        if not issues:
            self.stdout.write(
                self.style.SUCCESS("Audit OK: aucun fichier manquant détecté.")
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"Audit: {len(issues)} référence(s) de média introuvable(s)."
            )
        )
        for model_label, object_pk, field_name, file_path in issues:
            self.stdout.write(
                f"- {model_label}#{object_pk} [{field_name}] -> {file_path}"
            )

        if options["repair"]:
            self.stdout.write(
                self.style.SUCCESS("Réparation terminée: références manquantes réinitialisées.")
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Lancez la commande avec --repair pour réinitialiser les champs cassés."
                )
            )
