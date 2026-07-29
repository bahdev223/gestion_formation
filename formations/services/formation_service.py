from django.db import transaction

from formations.models import Formation


@transaction.atomic
def create_formation(data, user=None):
    return Formation.objects.create(**data)


@transaction.atomic
def archive_formation(formation, user=None):
    formation.statut = Formation.Statut.ARCHIVEE
    formation.save(update_fields=["statut", "updated_at"])
    return formation


@transaction.atomic
def reactivate_formation(formation, user=None):
    formation.statut = Formation.Statut.ACTIVE
    formation.save(update_fields=["statut", "updated_at"])
    return formation

