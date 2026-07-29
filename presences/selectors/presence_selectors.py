from presences.models import Presence


def get_session_presences(session):
    return Presence.objects.filter(seance__session=session)

