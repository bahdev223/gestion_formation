from django.db import transaction

from formations.models import Seance


@transaction.atomic
def create_seance(session, data, user=None):
    return Seance.objects.create(session=session, **data)


@transaction.atomic
def complete_seance(seance, user=None):
    seance.statut = Seance.Statut.TERMINEE
    seance.save(update_fields=["statut", "updated_at"])
    return seance


@transaction.atomic
def cancel_seance(seance, reason, user=None):
    seance.statut = Seance.Statut.ANNULEE
    seance.observations = f"{seance.observations}\n\nAnnulation: {reason}".strip()
    seance.save(update_fields=["statut", "observations", "updated_at"])
    return seance

