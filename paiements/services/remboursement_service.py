from django.db import transaction

from paiements.models import Remboursement


@transaction.atomic
def create_refund(payment, amount, reason, user):
    return Remboursement.objects.create(
        paiement=payment,
        montant=amount,
        motif=reason,
        mode_remboursement=payment.mode_paiement,
        effectue_par=user,
    )

