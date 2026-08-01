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
from comptabilite_ohada.services.regle_service import RegleComptableService

from ..catalogue import SensFlux, obtenir


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
        if definition.code == "TRANSFERT":
            if operation.compte_destination is None:
                raise ValidationError("Un transfert exige un compte de destination.")
            if operation.compte_destination_id == operation.compte_tresorerie_id:
                raise ValidationError(
                    "Le compte source et le compte de destination sont identiques."
                )
        return definition

    @classmethod
    @transaction.atomic
    def executer(cls, operation, user=None):
        """Valide l'operation et genere ses consequences comptables."""
        from ..models import Operation

        if operation.statut == Operation.Statut.VALIDEE:
            raise ValidationError("Cette opération est déjà validée.")
        if operation.statut == Operation.Statut.ANNULEE:
            raise ValidationError("Cette opération est annulée.")

        definition = cls.valider_coherence(operation)
        organisation = operation.organisation
        regle = RegleComptableService.resoudre(organisation, definition.regle)

        ecriture = cls._comptabiliser(operation, definition, regle, user)

        operation.ecriture = ecriture
        operation.statut = Operation.Statut.VALIDEE
        operation.validee_par = user if user and user.is_authenticated else None
        operation.validee_le = timezone.now()
        operation.save(
            update_fields=[
                "ecriture",
                "statut",
                "validee_par",
                "validee_le",
                "updated_at",
            ]
        )
        return operation

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

        if definition.code == "TRANSFERT":
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

        compte_debit = EcritureService.get_compte(debit_code)
        compte_credit = EcritureService.get_compte(credit_code)
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
