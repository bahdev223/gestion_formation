from django.db import transaction

from formations.models import SessionFormation


@transaction.atomic
def create_session(data, user=None):
    return SessionFormation.objects.create(**data)


@transaction.atomic
def change_session_status(session, status, user=None):
    session.statut = status
    session.save(update_fields=["statut", "updated_at"])
    return session


@transaction.atomic
def cancel_session(session, reason, user=None):
    session.statut = SessionFormation.Statut.ANNULEE
    session.notes = f"{session.notes}\n\nAnnulation: {reason}".strip()
    session.save(update_fields=["statut", "notes", "updated_at"])
    return session

