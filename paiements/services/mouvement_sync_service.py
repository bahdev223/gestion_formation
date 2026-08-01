from __future__ import annotations

from dataclasses import dataclass

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from comptes.models import (
    MouvementCompte,
    NatureMouvement,
    SensMouvement,
    StatutMouvement,
)
from comptes.services import MouvementCompteService
from paiements.models import Paiement


@dataclass(frozen=True)
class PaymentMovementSyncResult:
    mouvement: MouvementCompte | None
    created: bool = False
    linked: bool = False
    skipped_reason: str = ""


def _payment_content_type():
    return ContentType.objects.get_for_model(Paiement)


def get_payment_movement(payment: Paiement) -> MouvementCompte | None:
    """Retourne le mouvement financier lie a un paiement de formation."""
    if not payment.pk:
        return None

    return (
        MouvementCompte.objects.filter(
            content_type=_payment_content_type(),
            object_id=payment.pk,
            nature=NatureMouvement.ENCAISSEMENT,
            sens=SensMouvement.ENTREE,
        )
        .order_by("id")
        .first()
    )


def find_unlinked_payment_movement(payment: Paiement) -> MouvementCompte | None:
    """Retrouve un ancien mouvement probable, cree sans liaison generique.

    Cela evite de creer un doublon si un paiement avait deja genere une entree
    de tresorerie avant l'ajout du lien content_type/object_id.
    """
    references = [payment.numero_recu]
    if payment.reference_transaction:
        references.append(payment.reference_transaction)

    return (
        MouvementCompte.objects.filter(
            compte=payment.compte,
            montant=payment.montant,
            nature=NatureMouvement.ENCAISSEMENT,
            sens=SensMouvement.ENTREE,
            reference__in=references,
            object_id__isnull=True,
            content_type__isnull=True,
        )
        .order_by("id")
        .first()
    )


@transaction.atomic
def ensure_payment_movement(
    payment: Paiement,
    user=None,
) -> PaymentMovementSyncResult:
    """Garantit qu'un paiement valide alimente exactement un compte financier.

    La methode est idempotente : l'appeler plusieurs fois sur le meme paiement
    ne doit jamais gonfler le solde du compte ni dupliquer les mouvements.
    """
    if payment.statut != Paiement.Statut.VALIDE:
        return PaymentMovementSyncResult(None, skipped_reason="paiement_non_valide")
    if not payment.compte_id:
        return PaymentMovementSyncResult(None, skipped_reason="compte_absent")

    payment = (
        Paiement.objects.select_related("compte", "enregistre_par")
        .select_for_update()
        .get(pk=payment.pk)
    )

    existing = get_payment_movement(payment)
    if existing:
        return PaymentMovementSyncResult(existing)

    unlinked = find_unlinked_payment_movement(payment)
    if unlinked:
        unlinked.content_type = _payment_content_type()
        unlinked.object_id = payment.pk
        unlinked.save(update_fields=["content_type", "object_id"])
        return PaymentMovementSyncResult(unlinked, linked=True)

    mouvement = MouvementCompteService.encaisser(
        compte=payment.compte,
        montant=payment.montant,
        libelle=f"Paiement formation {payment.numero_recu}",
        user=user or payment.enregistre_par,
        reference=payment.reference_transaction or payment.numero_recu,
        source=payment,
    )
    return PaymentMovementSyncResult(mouvement, created=True)


@transaction.atomic
def reverse_payment_movement(payment: Paiement, reason: str, user=None) -> MouvementCompte | None:
    """Annule le mouvement financier lie a un paiement annule."""
    mouvement = get_payment_movement(payment)
    if not mouvement or mouvement.statut == StatutMouvement.ANNULE:
        return None

    return MouvementCompteService.annuler(
        mouvement,
        user=user or payment.annule_par or payment.enregistre_par,
        raison=reason,
    )
