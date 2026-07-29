from formations.models import Formation, SessionFormation


def get_active_formations():
    return Formation.objects.filter(statut=Formation.Statut.ACTIVE)


def get_upcoming_sessions():
    return SessionFormation.objects.filter(statut__in=[SessionFormation.Statut.PLANIFIEE, SessionFormation.Statut.INSCRIPTIONS_OUVERTES])

