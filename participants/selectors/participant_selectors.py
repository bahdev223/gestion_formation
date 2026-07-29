from participants.models import Participant


def get_active_participants():
    return Participant.objects.filter(statut=Participant.Statut.ACTIF)

