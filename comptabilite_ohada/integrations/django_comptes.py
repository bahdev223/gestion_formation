"""Intégration atomique entre les comptes financiers et la comptabilité."""

from datetime import date

from django.dispatch import receiver


def connect():
    from comptes.models import NatureMouvement
    from comptes.signals.mouvement import (
        mouvement_annule,
        mouvement_valide,
        transfert_effectue,
    )
    from comptabilite_ohada.services.ecriture_service import EcritureService

    @receiver(
        mouvement_valide,
        dispatch_uid="comptabilite.mouvement_valide",
    )
    def on_mouvement_valide(
        sender, instance, nature, montant, user, **kwargs
    ):
        compte_code = instance.compte.compte_comptable_code or "571"
        if nature == NatureMouvement.ENCAISSEMENT:
            EcritureService.creer_ecriture_vente(
                compte_caisse_code=compte_code,
                montant=montant,
                libelle=instance.libelle,
                compte_produit_code="706",
                user=user,
            )
        elif nature == NatureMouvement.DECAISSEMENT:
            EcritureService.creer_ecriture_charge(
                compte_caisse_code=compte_code,
                montant=montant,
                libelle=instance.libelle,
                compte_charge_code="658",
                user=user,
            )
        # Un transfert est comptabilisé une seule fois par
        # on_transfert_effectue, après les deux mouvements financiers.

    @receiver(
        transfert_effectue,
        dispatch_uid="comptabilite.transfert_effectue",
    )
    def on_transfert_effectue(
        sender, instance, source, destination, montant, user, **kwargs
    ):
        source_code = source.compte_comptable_code or "571"
        destination_code = destination.compte_comptable_code or "571"
        EcritureService.creer_ecriture_transfert(
            compte_source_code=source_code,
            compte_dest_code=destination_code,
            montant=montant,
            libelle=(
                instance.notes
                or f"Virement {source.nom} → {destination.nom}"
            ),
            user=user,
        )

    @receiver(
        mouvement_annule,
        dispatch_uid="comptabilite.mouvement_annule",
    )
    def on_mouvement_annule(
        sender, instance, annulation, user, **kwargs
    ):
        compte_code = instance.compte.compte_comptable_code or "571"
        caisse = EcritureService.get_compte(compte_code)
        if instance.nature == NatureMouvement.ENCAISSEMENT:
            contrepartie = EcritureService.get_compte("706")
            lignes = [
                {
                    "compte": contrepartie,
                    "debit": instance.montant,
                    "libelle": f"Annulation {instance.libelle}",
                },
                {
                    "compte": caisse,
                    "credit": instance.montant,
                    "libelle": f"Annulation {instance.libelle}",
                },
            ]
        elif instance.nature == NatureMouvement.DECAISSEMENT:
            contrepartie = EcritureService.get_compte("658")
            lignes = [
                {
                    "compte": caisse,
                    "debit": instance.montant,
                    "libelle": f"Annulation {instance.libelle}",
                },
                {
                    "compte": contrepartie,
                    "credit": instance.montant,
                    "libelle": f"Annulation {instance.libelle}",
                },
            ]
        else:
            return
        EcritureService.creer_ecriture(
            reference=EcritureService.generer_reference("ANN"),
            date_ecriture=date.today(),
            libelle=f"Annulation {instance.reference or instance.libelle}",
            journal=EcritureService.get_or_create_journal(
                "OD", "Opérations diverses", "OD"
            ),
            lignes=lignes,
            user=user,
        )
