"""Intégration atomique entre les comptes financiers et la comptabilité.

Un mouvement de trésorerie est un événement métier : ce module l'écoute et
laisse le moteur en déduire l'écriture. Aucun code de compte n'apparaît ici —
ils viennent de RegleComptable, modifiable par entreprise.
"""

from datetime import date

from django.dispatch import receiver


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
        # Le tenant vient du compte mouvementé : c'est la seule source fiable
        # ici. Sans lui, l'écriture était rattachée au premier exercice ouvert
        # trouvé, donc potentiellement à une autre entreprise.
        organisation = instance.compte.organisation
        compte_code = _compte_tresorerie(instance.compte)

        if nature == NatureMouvement.ENCAISSEMENT:
            regle = RegleComptableService.resoudre(
                organisation, TypeOperationComptable.ENCAISSEMENT
            )
            EcritureService.creer_ecriture_vente(
                compte_caisse_code=compte_code,
                montant=montant,
                libelle=instance.libelle,
                compte_produit_code=regle["compte_credit"],
                organisation=organisation,
                user=user,
            )
        elif nature == NatureMouvement.DECAISSEMENT:
            regle = RegleComptableService.resoudre(
                organisation, TypeOperationComptable.DECAISSEMENT
            )
            EcritureService.creer_ecriture_charge(
                compte_caisse_code=compte_code,
                montant=montant,
                libelle=instance.libelle,
                compte_charge_code=regle["compte_debit"],
                organisation=organisation,
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
        if source.organisation_id != destination.organisation_id:
            raise ValueError(
                "Transfert refusé : les deux comptes appartiennent à des "
                "organisations différentes."
            )
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

    @receiver(
        mouvement_annule,
        dispatch_uid="comptabilite.mouvement_annule",
    )
    def on_mouvement_annule(
        sender, instance, annulation, user, **kwargs
    ):
        organisation = instance.compte.organisation
        tresorerie = EcritureService.get_compte(
            _compte_tresorerie(instance.compte)
        )

        if instance.nature == NatureMouvement.ENCAISSEMENT:
            type_operation = TypeOperationComptable.ANNULATION_ENCAISSEMENT
        elif instance.nature == NatureMouvement.DECAISSEMENT:
            type_operation = TypeOperationComptable.ANNULATION_DECAISSEMENT
        else:
            return

        regle = RegleComptableService.resoudre(organisation, type_operation)
        # Un seul côté de la règle est renseigné : l'autre est la trésorerie.
        contrepartie_code = regle["compte_debit"] or regle["compte_credit"]
        contrepartie = EcritureService.get_compte(contrepartie_code)
        libelle = f"Annulation {instance.libelle}"

        if regle["compte_debit"]:
            # La contrepartie est débitée, la trésorerie créditée.
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
