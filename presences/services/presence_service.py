from django.db import transaction

from presences.models import Presence


@transaction.atomic
def save_presence(seance, inscription, status, user, **kwargs):
    presence, _ = Presence.objects.update_or_create(
        seance=seance,
        inscription=inscription,
        defaults={"statut": status, "enregistre_par": user, **kwargs},
    )
    return presence


@transaction.atomic
def bulk_save_presences(seance, records, user):
    items = []
    for record in records:
        items.append(save_presence(seance, record["inscription"], record["status"], user, **record.get("extra", {})))
    return items


def calculate_attendance_rate(inscription):
    total = inscription.presences.count()
    if total == 0:
        return 0
    points = 0
    for presence in inscription.presences.all():
        if presence.statut == Presence.Statut.PRESENT:
            points += 1
        elif presence.statut == Presence.Statut.RETARD:
            points += 0.5
    return (points / total) * 100

