from inscriptions.models import Inscription


def get_unpaid_inscriptions():
    return Inscription.objects.filter(statut_paiement=Inscription.StatutPaiement.NON_PAYE)

