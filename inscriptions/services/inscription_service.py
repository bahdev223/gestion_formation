from decimal import Decimal

from django.db import transaction

from inscriptions.models import Inscription


@transaction.atomic
def create_inscription(participant, session, data, user):
    prix_initial = getattr(session, "prix_applique", Decimal("0"))
    remise = data.get("remise", Decimal("0"))
    inscription = Inscription.objects.create(
        participant=participant,
        session=session,
        prix_initial=prix_initial,
        remise=remise,
        montant_final=prix_initial - remise,
        cree_par=user,
        **{k: v for k, v in data.items() if k != "remise"},
    )
    return inscription


@transaction.atomic
def confirm_inscription(inscription, user):
    inscription.statut = Inscription.Statut.CONFIRME
    inscription.save(update_fields=["statut", "updated_at"])
    return inscription


@transaction.atomic
def cancel_inscription(inscription, reason, user):
    inscription.statut = Inscription.Statut.ANNULE
    inscription.motif_annulation = reason
    inscription.annulee_par = user
    inscription.save(update_fields=["statut", "motif_annulation", "annulee_par", "updated_at"])
    return inscription


def recalculate_payment_status(inscription):
    total = inscription.total_paye
    if total <= 0:
        inscription.statut_paiement = Inscription.StatutPaiement.NON_PAYE
    elif total < inscription.montant_final:
        inscription.statut_paiement = Inscription.StatutPaiement.PARTIEL
    elif total == inscription.montant_final:
        inscription.statut_paiement = Inscription.StatutPaiement.PAYE
    else:
        inscription.statut_paiement = Inscription.StatutPaiement.TROP_PERCU
    inscription.save(update_fields=["statut_paiement", "updated_at"])
    return inscription

