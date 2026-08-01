"""Intégration entre les comptes financiers et la comptabilité OHADA.

Un mouvement de trésorerie est un événement métier : ce module l'écoute et
laisse le moteur en déduire l'écriture. La trésorerie ne doit jamais être
bloquée parce que la comptabilité n'est pas encore totalement configurée.
"""

import logging
from datetime import date

from django.core.exceptions import ValidationError
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def connect():
    from comptes.models import NatureMouvement
    from comptes.signals.mouvement import (
        mouvement_annule,
        mouvement_valide,
        transfert_effectue,
    )
    from comptabilite_ohada.models import TypeOperationComptable
    from comptabilite_ohada.services.ecriture_service import EcritureService
    from comptabilite_ohada.services.regle_service import RegleComptableService

    def _compte_tresorerie(compte):
        """Compte comptable du compte de trésorerie mouvementé."""
        return compte.compte_comptable_code or (
            RegleComptableService.compte_tresorerie_defaut(compte.organisation)
        )

    @receiver(
        mouvement_valide,
        dispatch_uid="comptabilite.mouvement_valide",
    )
    def on_mouvement_valide(
        sender, instance, nature, montant, user, **kwargs
    ):
        organisation = instance.compte.organisation
        compte_code = _compte_tresorerie(instance.compte)

        if nature == NatureMouvement.ENCAISSEMENT:
            regle = RegleComptableService.resoudre(
                organisation, TypeOperationComptable.ENCAISSEMENT
            )
            try:
                EcritureService.creer_ecriture_vente(
                    compte_caisse_code=compte_code,
                    montant=montant,
                    libelle=instance.libelle,
                    compte_produit_code=regle["compte_credit"],
                    organisation=organisation,
                    user=user,
                )
            except ValidationError as exc:
                logger.warning(
                    "Ecriture comptable ignoree pour le mouvement %s: %s",
                    instance.pk,
                    exc,
                )
        elif nature == NatureMouvement.DECAISSEMENT:
            regle = RegleComptableService.resoudre(
                organisation, TypeOperationComptable.DECAISSEMENT
            )
            try:
                EcritureService.creer_ecriture_charge(
                    compte_caisse_code=compte_code,
                    montant=montant,
                    libelle=instance.libelle,
                    compte_charge_code=regle["compte_debit"],
                    organisation=organisation,
                    user=user,
                )
            except ValidationError as exc:
                logger.warning(
                    "Ecriture comptable ignoree pour le mouvement %s: %s",
                    instance.pk,
                    exc,
                )

    @receiver(
        transfert_effectue,
        dispatch_uid="comptabilite.transfert_effectue",
    )
    def on_transfert_effectue(
        sender, instance, source, destination, montant, user, **kwargs
    ):
        if source.organisation_id != destination.organisation_id:
            raise ValueError(
                "Transfert refusé : les deux comptes appartiennent à des "
                "organisations différentes."
            )
        try:
            EcritureService.creer_ecriture_transfert(
                compte_source_code=_compte_tresorerie(source),
                compte_dest_code=_compte_tresorerie(destination),
                montant=montant,
                libelle=(
                    instance.notes
                    or f"Virement {source.nom} → {destination.nom}"
                ),
                organisation=source.organisation,
                user=user,
            )
        except ValidationError as exc:
            logger.warning(
                "Ecriture comptable de transfert ignoree pour le transfert %s: %s",
                instance.pk,
                exc,
            )

    @receiver(
        mouvement_annule,
        dispatch_uid="comptabilite.mouvement_annule",
    )
    def on_mouvement_annule(
        sender, instance, annulation, user, **kwargs
    ):
        organisation = instance.compte.organisation

        if instance.nature == NatureMouvement.ENCAISSEMENT:
            type_operation = TypeOperationComptable.ANNULATION_ENCAISSEMENT
        elif instance.nature == NatureMouvement.DECAISSEMENT:
            type_operation = TypeOperationComptable.ANNULATION_DECAISSEMENT
        else:
            return

        try:
            tresorerie = EcritureService.get_compte(
                _compte_tresorerie(instance.compte)
            )
            regle = RegleComptableService.resoudre(organisation, type_operation)
            contrepartie_code = regle["compte_debit"] or regle["compte_credit"]
            contrepartie = EcritureService.get_compte(contrepartie_code)
            libelle = f"Annulation {instance.libelle}"

            if regle["compte_debit"]:
                lignes = [
                    {"compte": contrepartie, "debit": instance.montant, "libelle": libelle},
                    {"compte": tresorerie, "credit": instance.montant, "libelle": libelle},
                ]
            else:
                lignes = [
                    {"compte": tresorerie, "debit": instance.montant, "libelle": libelle},
                    {"compte": contrepartie, "credit": instance.montant, "libelle": libelle},
                ]

            EcritureService.creer_ecriture(
                reference=EcritureService.generer_reference("ANN"),
                date_ecriture=date.today(),
                libelle=f"Annulation {instance.reference or instance.libelle}",
                journal=EcritureService.get_or_create_journal(
                    regle["journal_code"], "Opérations diverses", "OD"
                ),
                lignes=lignes,
                organisation=organisation,
                user=user,
            )
        except ValidationError as exc:
            logger.warning(
                "Ecriture comptable d'annulation ignoree pour le mouvement %s: %s",
                instance.pk,
                exc,
            )
