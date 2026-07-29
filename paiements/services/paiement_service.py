from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from paiements.models import Paiement
from inscriptions.services.inscription_service import recalculate_payment_status


@transaction.atomic
def register_payment(inscription, amount, mode, user, **kwargs):
    payment = Paiement.objects.create(
        inscription=inscription,
        montant=amount,
        mode_paiement=mode,
        enregistre_par=user,
        **kwargs,
    )
    recalculate_payment_status(inscription)
    return payment


@transaction.atomic
def cancel_payment(payment, reason, user):
    payment.statut = Paiement.Statut.ANNULE
    payment.motif_annulation = reason
    payment.annule_par = user
    payment.date_annulation = timezone.now()
    payment.save(update_fields=["statut", "motif_annulation", "annule_par", "date_annulation", "updated_at"])
    recalculate_payment_status(payment.inscription)
    return payment
