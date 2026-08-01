
from django.db import transaction
from django.utils import timezone

from comptes.services import MouvementCompteService
from inscriptions.services.inscription_service import recalculate_payment_status
from paiements.models import Paiement


@transaction.atomic
def register_payment(inscription, amount, mode, user, compte=None, **kwargs):
    kwargs.setdefault("organisation", inscription.organisation)
    payment = Paiement.objects.create(
        inscription=inscription,
        montant=amount,
        mode_paiement=mode,
        compte=compte,
        enregistre_par=user,
        **kwargs,
    )
    if compte is not None:
        MouvementCompteService.encaisser(
            compte=compte,
            montant=amount,
            libelle=f"Paiement formation {payment.numero_recu}",
            user=user,
            reference=payment.reference_transaction or payment.numero_recu,
            source=payment,
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
