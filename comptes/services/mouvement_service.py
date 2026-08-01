from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from ..models import (
    MouvementCompte,
    NatureMouvement,
    SensMouvement,
    StatutMouvement,
)
from ..signals.mouvement import mouvement_annule, mouvement_valide


class MouvementCompteService:
    """Service metier des mouvements de compte."""

    @staticmethod
    def encaisser(
        compte, montant, libelle, user, reference=None, source=None, *,
        emettre_signal=True,
    ):
        return MouvementCompteService._creer(
            compte=compte,
            nature=NatureMouvement.ENCAISSEMENT,
            sens=SensMouvement.ENTREE,
            montant=montant,
            libelle=libelle,
            user=user,
            reference=reference,
            source=source,
            emettre_signal=emettre_signal,
        )

    @staticmethod
    def decaisser(
        compte, montant, libelle, user, reference=None, source=None, *,
        emettre_signal=True,
    ):
        montant = Decimal(str(montant))
        if compte.solde_disponible < montant:
            raise ValueError(
                f"Solde insuffisant. Disponible: {compte.solde_disponible:,.0f}, "
                f"Requis: {montant:,.0f}"
            )
        return MouvementCompteService._creer(
            compte=compte,
            nature=NatureMouvement.DECAISSEMENT,
            sens=SensMouvement.SORTIE,
            montant=montant,
            libelle=libelle,
            user=user,
            reference=reference,
            source=source,
            emettre_signal=emettre_signal,
        )

    @staticmethod
    def transfert(
        compte,
        montant,
        libelle,
        user,
        reference=None,
        source=None,
        sens=SensMouvement.ENTREE,
        emettre_signal=True,
    ):
        if sens not in SensMouvement.values:
            raise ValueError("Sens de transfert invalide")
        return MouvementCompteService._creer(
            compte=compte,
            nature=NatureMouvement.TRANSFERT,
            sens=sens,
            montant=montant,
            libelle=libelle,
            user=user,
            reference=reference,
            source=source,
            emettre_signal=emettre_signal,
        )

    @staticmethod
    def ajuster(compte, montant, libelle, user, reference=None, source=None):
        return MouvementCompteService._creer(
            compte=compte,
            nature=NatureMouvement.AJUSTEMENT,
            sens=SensMouvement.ENTREE,
            montant=montant,
            libelle=libelle,
            user=user,
            reference=reference,
            source=source,
        )

    @staticmethod
    @transaction.atomic
    def _creer(
        compte,
        nature,
        sens,
        montant,
        libelle,
        user,
        reference=None,
        source=None,
        emettre_signal=True,
    ):
        montant = Decimal(str(montant))
        if montant <= 0:
            raise ValueError("Le montant doit etre positif")

        mouvement = MouvementCompte.objects.create(
            compte=compte,
            nature=nature,
            sens=sens,
            statut=StatutMouvement.VALIDE,
            montant=montant,
            libelle=libelle,
            reference=reference,
            created_by=user,
        )

        if source:
            from django.contrib.contenttypes.models import ContentType

            ct = ContentType.objects.get_for_model(source)
            mouvement.content_type = ct
            mouvement.object_id = source.pk
            mouvement.save(update_fields=["content_type", "object_id"])

        MouvementCompteService._mettre_a_jour_solde(compte, sens, montant)

        if emettre_signal:
            mouvement_valide.send(
                sender=MouvementCompteService,
                instance=mouvement,
                nature=nature,
                montant=montant,
                user=user,
            )

        return mouvement

    @staticmethod
    @transaction.atomic
    def annuler(mouvement, user, raison=""):
        if mouvement.statut == StatutMouvement.ANNULE:
            raise ValueError("Ce mouvement est deja annule")
        if mouvement.nature == NatureMouvement.TRANSFERT:
            raise ValueError(
                "Un transfert ne peut pas être annulé isolément. "
                "Effectuez un transfert inverse."
            )

        mouvement.statut = StatutMouvement.ANNULE
        mouvement.annule = True
        mouvement.annule_le = timezone.now()
        mouvement.annule_par = user
        mouvement.save(update_fields=["statut", "annule", "annule_le", "annule_par"])

        annulation = MouvementCompte.objects.create(
            compte=mouvement.compte,
            nature=NatureMouvement.ANNULATION,
            sens=(
                SensMouvement.SORTIE
                if mouvement.est_entree
                else SensMouvement.ENTREE
            ),
            statut=StatutMouvement.VALIDE,
            montant=mouvement.montant,
            libelle=f"ANNULATION - {mouvement.libelle} - {raison}".strip(),
            reference=mouvement.reference,
            created_by=user,
            mouvement_parent=mouvement,
        )

        MouvementCompteService._mettre_a_jour_solde(
            mouvement.compte, annulation.sens, mouvement.montant
        )

        mouvement_annule.send(
            sender=MouvementCompteService,
            instance=mouvement,
            annulation=annulation,
            user=user,
        )

        return annulation

    @staticmethod
    def _mettre_a_jour_solde(compte, sens, montant):
        sign = 1 if sens == SensMouvement.ENTREE else -1

        compte.solde_actuel += sign * montant
        compte.save(update_fields=["solde_actuel"])
