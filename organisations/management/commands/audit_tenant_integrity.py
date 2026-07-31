from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import OrganisationOwnedModel
from organisations.models import Organisation


class Command(BaseCommand):
    help = (
        "Detecte les donnees metier sans organisation et peut les rattacher "
        "automatiquement lorsqu'une seule organisation existe."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix-single-tenant",
            action="store_true",
            help=(
                "Rattacher les lignes orphelines a l'unique organisation. "
                "Refuse de choisir si plusieurs organisations existent."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        organisations = list(Organisation.objects.order_by("pk")[:2])
        orphaned = []

        for model in apps.get_models():
            if not issubclass(model, OrganisationOwnedModel):
                continue
            try:
                field = model._meta.get_field("organisation")
            except Exception:
                continue
            if not field.null:
                continue
            count = model.objects.filter(organisation__isnull=True).count()
            if count:
                orphaned.append((model, count))

        if not orphaned:
            self.stdout.write(
                self.style.SUCCESS(
                    "Integrite tenant validee : aucune donnee orpheline."
                )
            )
            return

        details = ", ".join(
            f"{model._meta.label}: {count}"
            for model, count in orphaned
        )
        if not options["fix_single_tenant"]:
            raise CommandError(
                "Donnees sans organisation detectees. "
                f"{details}. Relancez avec --fix-single-tenant uniquement "
                "si cette base appartient a une seule entreprise."
            )
        if len(organisations) != 1:
            raise CommandError(
                "--fix-single-tenant exige exactement une organisation. "
                f"Donnees detectees : {details}."
            )

        organisation = organisations[0]
        for model, _ in orphaned:
            model.objects.filter(organisation__isnull=True).update(
                organisation=organisation
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Donnees rattachees a {organisation.nom} : {details}."
            )
        )
