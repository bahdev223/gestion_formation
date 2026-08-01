"""Moteur d'execution des operations.

Recoit une Operation declaree en termes metier et en deduit ses consequences :
mouvement de tresorerie puis ecriture comptable. Aucun code de compte
n'apparait ici : ils viennent de RegleComptable, donc modifiables par
entreprise sans toucher au code.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from comptabilite_ohada.services.ecriture_service import EcritureService
from comptabilite_ohada.services.initialisation_service import InitialisationService
from comptabilite_ohada.services.regle_service import RegleComptableService

from ..catalogue import ClasseOperation, SensFlux, obtenir

OPERATIONS_ENTRE_COMPTES = frozenset(
    {"TRANSFERT", "DEPOT_BANQUE", "RETRAIT_BANQUE"}
)


class OperationEngine:
    @staticmethod
    def numeroter(organisation, date_operation):
        """Numero sequentiel par organisation et par annee."""
        from ..models import Operation

        prefixe = f"OP-{date_operation.year}"
        dernier = (
            Operation.objects.filter(
                organisation=organisation, numero__startswith=prefixe
            )
            .order_by("-numero")
            .values_list("numero", flat=True)
            .first()
        )
        suivant = 1
        if dernier:
            try:
                suivant = int(dernier.rsplit("-", 1)[1]) + 1
            except (IndexError, ValueError):
                suivant = 1
        return f"{prefixe}-{suivant:05d}"

    @staticmethod
    def valider_coherence(operation):
        """Controles metier avant execution.

        Verifie aussi que les comptes designes appartiennent bien a
        l'organisation de l'operation : un identifiant venu d'un formulaire ne
        doit jamais permettre de mouvementer la tresorerie d'un autre client.
        """
        definition = obtenir(operation.type_operation)
        if definition is None:
            raise ValidationError(
                f"Type d'opération inconnu : {operation.type_operation}."
            )
        if operation.organisation_id is None:
            raise ValidationError(
                "Une opération doit appartenir à une organisation."
            )
        if operation.montant is None or operation.montant <= 0:
            raise ValidationError("Le montant doit être strictement positif.")

        for champ in ("compte_tresorerie", "compte_destination"):
            compte = getattr(operation, champ, None)
            if compte is not None and compte.organisation_id != operation.organisation_id:
                raise ValidationError(
                    "Le compte sélectionné appartient à une autre organisation."
                )

        if definition.exige_compte_tresorerie and operation.compte_tresorerie is None:
            raise ValidationError(
                "Cette opération nécessite un compte de trésorerie."
            )
        if definition.code in OPERATIONS_ENTRE_COMPTES:
            if operation.compte_destination is None:
                raise ValidationError(
                    "Cette opération exige un compte de destination."
                )
            if operation.compte_destination_id == operation.compte_tresorerie_id:
                raise ValidationError(
                    "Le compte source et le compte de destination sont identiques."
                )
        return definition

    @classmethod
    @transaction.atomic
    def executer(cls, operation, user=None):
        """Valide l'operation, actualise la tresorerie et la comptabilite.

        Tout est atomique : si le mouvement financier ou l'ecriture echoue,
        aucun solde partiel n'est conserve. Le verrou sur l'operation empeche
        aussi un double clic de mouvementer deux fois le meme montant.
        """
        from comptes.models import Compte

        from ..models import Operation

        operation_initiale = operation
        # Verrouiller uniquement l'operation. Les deux comptes sont nullable :
        # select_related() produisait des LEFT JOIN et PostgreSQL refuse
        # FOR UPDATE sur le cote nullable d'une jointure externe. Les comptes
        # de tresorerie sont verrouilles separement juste apres.
        operation = Operation.objects.select_for_update().get(pk=operation.pk)

        if operation.statut == Operation.Statut.VALIDEE:
            raise ValidationError("Cette opération est déjà validée.")
        if operation.statut == Operation.Statut.ANNULEE:
            raise ValidationError("Cette opération est annulée.")

        definition = cls.valider_coherence(operation)
        organisation = operation.organisation

        compte_ids = {
            compte_id
            for compte_id in (
                operation.compte_tresorerie_id,
                operation.compte_destination_id,
            )
            if compte_id
        }
        comptes_verrouilles = {
            compte.pk: compte
            for compte in Compte.objects.select_for_update()
            .filter(pk__in=compte_ids)
            .order_by("pk")
        }
        if operation.compte_tresorerie_id:
            operation.compte_tresorerie = comptes_verrouilles[
                operation.compte_tresorerie_id
            ]
        if operation.compte_destination_id:
            operation.compte_destination = comptes_verrouilles[
                operation.compte_destination_id
            ]

        InitialisationService.initialiser_organisation(
            organisation, date_reference=operation.date_operation
        )
        regle = RegleComptableService.resoudre(organisation, definition.regle)

        mouvement = cls._mouvementer(operation, definition, user)
        ecriture = cls._comptabiliser(operation, definition, regle, user)

        operation.mouvement = mouvement
        operation.ecriture = ecriture
        operation.statut = Operation.Statut.VALIDEE
        operation.validee_par = user if user and user.is_authenticated else None
        operation.validee_le = timezone.now()
        operation.save(
            update_fields=[
                "ecriture",
                "mouvement",
                "statut",
                "validee_par",
                "validee_le",
                "updated_at",
            ]
        )
        # Les appelants historiques reutilisent l'instance transmise sans la
        # recharger. On leur restitue donc l'etat obtenu sous verrou.
        operation_initiale.mouvement = mouvement
        operation_initiale.ecriture = ecriture
        operation_initiale.statut = operation.statut
        operation_initiale.validee_par = operation.validee_par
        operation_initiale.validee_le = operation.validee_le
        return operation

    @staticmethod
    def _mouvementer(operation, definition, user):
        """Produit l'impact financier sans declencher une seconde ecriture.

        Le moteur d'operations genere lui-meme l'ecriture adaptee au type
        choisi. Les signaux comptables generiques des comptes sont donc
        desactives ici pour garantir une seule ecriture par operation.
        """
        from comptes.models import SensMouvement
        from comptes.services import MouvementCompteService

        if not operation.compte_tresorerie_id:
            return None

        commun = {
            "montant": operation.montant,
            "user": user,
            "reference": operation.numero,
            "source": operation,
            "emettre_signal": False,
        }
        try:
            if definition.sens == SensFlux.ENTREE:
                return MouvementCompteService.encaisser(
                    compte=operation.compte_tresorerie,
                    libelle=operation.description,
                    **commun,
                )
            if definition.sens == SensFlux.SORTIE:
                return MouvementCompteService.decaisser(
                    compte=operation.compte_tresorerie,
                    libelle=operation.description,
                    **commun,
                )
            if definition.code in OPERATIONS_ENTRE_COMPTES:
                sortie = MouvementCompteService.transfert(
                    compte=operation.compte_tresorerie,
                    libelle=f"{operation.description} vers {operation.compte_destination.nom}",
                    sens=SensMouvement.SORTIE,
                    **commun,
                )
                MouvementCompteService.transfert(
                    compte=operation.compte_destination,
                    libelle=f"{operation.description} depuis {operation.compte_tresorerie.nom}",
                    sens=SensMouvement.ENTREE,
                    **commun,
                )
                return sortie
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        return None

    @classmethod
    def _comptabiliser(cls, operation, definition, regle, user):
        """Construit l'ecriture a partir de la regle resolue.

        Un cote de la regle peut etre vide : il est alors fourni par
        l'operation (le compte de tresorerie reellement mouvemente).
        """
        organisation = operation.organisation
        journal = EcritureService.get_or_create_journal(
            regle["journal_code"], regle["libelle"], "OD"
        )

        if definition.code in OPERATIONS_ENTRE_COMPTES:
            return EcritureService.creer_ecriture_transfert(
                compte_source_code=cls._code_tresorerie(operation.compte_tresorerie, organisation),
                compte_dest_code=cls._code_tresorerie(operation.compte_destination, organisation),
                montant=operation.montant,
                libelle=operation.description,
                organisation=organisation,
                user=user,
            )

        debit_code = regle["compte_debit"]
        credit_code = regle["compte_credit"]
        if definition.classe == ClasseOperation.CHARGES:
            compte_charge = (operation.donnees or {}).get("compte_charge")
            if compte_charge:
                if not str(compte_charge).startswith("6"):
                    raise ValidationError(
                        "Le compte de depense doit etre un compte de charge."
                    )
                debit_code = str(compte_charge)
        tresorerie_code = (
            cls._code_tresorerie(operation.compte_tresorerie, organisation)
            if operation.compte_tresorerie
            else None
        )

        # Le cote vide de la regle est complete par la tresorerie.
        if not debit_code:
            debit_code = tresorerie_code
        if not credit_code:
            credit_code = tresorerie_code
        if not debit_code or not credit_code:
            raise ValidationError(
                "La règle comptable est incomplète pour ce type d'opération : "
                "aucun compte ne peut être déterminé."
            )

        compte_debit = EcritureService.get_compte(
            debit_code, organisation=organisation
        )
        compte_credit = EcritureService.get_compte(
            credit_code, organisation=organisation
        )
        if compte_debit is None or compte_credit is None:
            raise ValidationError(
                "Les comptes de la règle comptable sont introuvables dans le "
                "plan comptable."
            )

        return EcritureService.creer_ecriture(
            reference=operation.numero,
            date_ecriture=operation.date_operation,
            libelle=operation.description,
            journal=journal,
            lignes=[
                {
                    "compte": compte_debit,
                    "debit": operation.montant,
                    "libelle": operation.description,
                },
                {
                    "compte": compte_credit,
                    "credit": operation.montant,
                    "libelle": operation.description,
                },
            ],
            organisation=organisation,
            user=user,
        )

    @staticmethod
    def _code_tresorerie(compte, organisation):
        if compte is None:
            return None
        return compte.compte_comptable_code or (
            RegleComptableService.compte_tresorerie_defaut(organisation)
        )

    @staticmethod
    def sens_libelle(definition):
        return {
            SensFlux.ENTREE: "Entrée",
            SensFlux.SORTIE: "Sortie",
            SensFlux.NEUTRE: "Neutre",
        }.get(definition.sens, "")
