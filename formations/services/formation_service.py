from django.db import transaction

from formations.models import Formation
from subscriptions.services import QuotaService


@transaction.atomic
def create_formation(data, user=None):
    organisation = data.get("organisation")
    if data.get("statut") == Formation.Statut.ACTIVE:
        QuotaService.require_active_formation_slot(organisation)
    return Formation.objects.create(**data)


@transaction.atomic
def archive_formation(formation, user=None):
    formation.statut = Formation.Statut.ARCHIVEE
    formation.save(update_fields=["statut", "updated_at"])
    return formation


@transaction.atomic
def reactivate_formation(formation, user=None):
    QuotaService.require_active_formation_slot(formation.organisation)
    formation.statut = Formation.Statut.ACTIVE
    formation.save(update_fields=["statut", "updated_at"])
    return formation
