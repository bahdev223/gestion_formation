from django.core.exceptions import ValidationError
from django.db import transaction

from presences.models import Presence


@transaction.atomic
def save_presence(seance, inscription, status, user, **kwargs):
    if inscription.session_id != seance.session_id:
        raise ValidationError(
            "Impossible d'enregistrer une présence pour une autre session."
        )
    if status not in Presence.Statut.values:
        raise ValidationError("Statut de présence invalide.")
    presence, _ = Presence.objects.update_or_create(
        seance=seance,
        inscription=inscription,
        defaults={
            "organisation": seance.organisation or inscription.organisation,
            "statut": status,
            "enregistre_par": user,
            **kwargs,
        },
    )
    return presence


@transaction.atomic
def bulk_save_presences(seance, records, user):
    items = []
    for record in records:
        items.append(save_presence(seance, record["inscription"], record["status"], user, **record.get("extra", {})))
    return items


def calculate_attendance_rate(inscription):
    presences = inscription.presences.exclude(
        seance__statut="ANNULEE"
    )
    total = presences.count()
    if total == 0:
        return 0
    points = 0
    for presence in presences:
        if presence.statut == Presence.Statut.PRESENT:
            points += 1
        elif presence.statut == Presence.Statut.RETARD:
            points += 0.5
    return (points / total) * 100
