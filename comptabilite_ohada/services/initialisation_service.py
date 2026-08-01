import json
from datetime import date
from decimal import Decimal
from importlib.resources import files as pkg_files

from django.db import transaction

from ..models import (
    CompteComptable,
    ConfigurationComptable,
    ExerciceComptable,
    JournalComptable,
    SoldeInitialComptable,
)
from .ecriture_service import EcritureService


class InitialisationService:
    """Initialisation du plan comptable SYSCOHADA et de la configuration."""

    @staticmethod
    @transaction.atomic
    def charger_plan_comptable(force=False, *, organisation=None):
        try:
            content = pkg_files("comptabilite_ohada.data").joinpath("plan_comptable.json").read_text(encoding="utf-8")
        except (ImportError, FileNotFoundError):
            return {"success": False, "error": "Fichier plan_comptable.json introuvable"}

        data = json.loads(content)
        comptes_data = data.get("comptes", [])
        if not comptes_data:
            return {"success": False, "error": "Aucun compte dans le fichier"}

        scope = CompteComptable.objects.filter(organisation=organisation)
        existants = {compte.code: compte for compte in scope}
        nouveaux = []
        a_mettre_a_jour = []
        champs = [
            "libelle", "nature", "sens", "niveau", "type_compte",
            "est_mouvement", "categorie", "actif",
        ]
        for item in comptes_data:
            code = str(item["code"])
            valeurs = {
                "libelle": item["libelle"],
                "nature": item.get("nature", "NEUTRE"),
                "sens": item.get("sens", "MIXTE"),
                "niveau": item.get("niveau", 1),
                "type_compte": item.get("type", item.get("type_compte", "compte")),
                "est_mouvement": item.get("est_mouvement", True),
                "categorie": item.get("categorie", "bilan"),
                "actif": item.get("actif", True),
            }
            compte = existants.get(code)
            if compte is None:
                nouveaux.append(
                    CompteComptable(
                        organisation=organisation,
                        code=code,
                        **valeurs,
                    )
                )
            elif force:
                for champ, valeur in valeurs.items():
                    setattr(compte, champ, valeur)
                a_mettre_a_jour.append(compte)

        if nouveaux:
            CompteComptable.objects.bulk_create(nouveaux, batch_size=250)
        if a_mettre_a_jour:
            CompteComptable.objects.bulk_update(
                a_mettre_a_jour, champs, batch_size=250
            )

        comptes = {
            compte.code: compte
            for compte in CompteComptable.objects.filter(
                organisation=organisation,
                code__in=[str(item["code"]) for item in comptes_data],
            )
        }
        parents_modifies = []
        for item in comptes_data:
            parent_code = item.get("parent", item.get("parent_code"))
            compte = comptes[str(item["code"])]
            parent = comptes.get(str(parent_code)) if parent_code else None
            if compte.parent_id != getattr(parent, "pk", None):
                compte.parent = parent
                parents_modifies.append(compte)
        if parents_modifies:
            CompteComptable.objects.bulk_update(
                parents_modifies, ["parent"], batch_size=250
            )

        return {
            "success": True,
            "comptes_crees": len(nouveaux),
            "total": len(comptes_data),
            "organisation_id": getattr(organisation, "pk", None),
        }

    @classmethod
    @transaction.atomic
    def initialiser_organisation(cls, organisation, date_reference=None):
        """Garantit un plan, des regles et un exercice ouverts pour le tenant."""
        if organisation is None:
            raise ValueError("L'organisation est obligatoire.")
        date_reference = date_reference or date.today()
        if CompteComptable.objects.filter(organisation=organisation).exists():
            plan = {
                "success": True,
                "comptes_crees": 0,
                "total": CompteComptable.objects.filter(
                    organisation=organisation
                ).count(),
                "organisation_id": organisation.pk,
            }
        else:
            plan = cls.charger_plan_comptable(organisation=organisation)
        cls.initialiser_journaux()

        from .regle_service import RegleComptableService

        RegleComptableService.initialiser(organisation)
        exercice, _ = ExerciceComptable.objects.get_or_create(
            organisation=organisation,
            date_debut=date(date_reference.year, 1, 1),
            date_fin=date(date_reference.year, 12, 31),
            defaults={"code": f"{organisation.pk}-{date_reference.year}"},
        )
        configuration = ConfigurationComptable.get_config(
            organisation=organisation
        )
        champs_configuration = []
        if configuration.exercice_id != exercice.pk:
            configuration.exercice = exercice
            champs_configuration.append("exercice")
        if not configuration.est_initialise:
            configuration.est_initialise = True
            configuration.date_initialisation = date_reference
            champs_configuration.extend(["est_initialise", "date_initialisation"])
        if configuration.devise != organisation.devise:
            configuration.devise = organisation.devise
            champs_configuration.append("devise")
        if champs_configuration:
            configuration.save(update_fields=champs_configuration + ["updated_at"])
        return {"plan": plan, "exercice": exercice, "configuration": configuration}

    @staticmethod
    @transaction.atomic
    def initialiser_journaux():
        defaults = [
            ("VN", "Ventes", "VENTES"),
            ("AC", "Achats", "ACHATS"),
            ("BQ", "Banque", "BANQUE"),
            ("CS", "Caisse", "CAISSE"),
            ("OD", "Opérations Diverses", "OD"),
            ("PA", "Paie", "PAIE"),
            ("ST", "Stock", "STOCK"),
            ("INV", "Immobilisations", "IMMO"),
            ("TR", "Transferts", "BANQUE"),
        ]
        for code, libelle, type_j in defaults:
            JournalComptable.objects.get_or_create(
                code=code,
                defaults={"libelle": libelle, "type_journal": type_j, "actif": True},
            )

    @staticmethod
    def initialiser_soldes(soldes, *, organisation, user=None):
        if organisation is None:
            raise ValueError("L'organisation est obligatoire.")
        config = ConfigurationComptable.get_config(organisation=organisation)
        solde_init, _ = SoldeInitialComptable.objects.get_or_create(configuration=config)
        for field, value in soldes.items():
            if hasattr(solde_init, field):
                setattr(solde_init, field, Decimal(str(value)))
        solde_init.save()

        exercice = ExerciceComptable.objects.filter(
            organisation=organisation,
            cloture=False,
        ).first()
        if not exercice:
            return solde_init

        contrepartie = config.contrepartie_situation
        mapping = {
            "caisse": "571",
            "banque": "521",
            "stocks": "31",
            "clients": "411",
            "fournisseurs": "401",
        }
        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        lignes = []

        for field, compte_code in mapping.items():
            montant = getattr(solde_init, field, Decimal("0.00"))
            if montant > 0:
                if field in ("fournisseurs",):
                    lignes.append({"compte": EcritureService.get_compte(compte_code),
                                   "credit": montant})
                    total_credit += montant
                else:
                    lignes.append({"compte": EcritureService.get_compte(compte_code),
                                   "debit": montant})
                    total_debit += montant

        if total_debit != total_credit:
            ecart = total_debit - total_credit
            if ecart > 0:
                lignes.append({"compte": EcritureService.get_compte(contrepartie),
                               "credit": ecart})
            else:
                lignes.append({"compte": EcritureService.get_compte(contrepartie),
                               "debit": -ecart})

        EcritureService.creer_ecriture(
            reference=f"SI-{date.today().strftime('%Y%m%d')}",
            date_ecriture=date.today(),
            libelle="Situation initiale",
            journal=EcritureService.get_or_create_journal("OD", "OD", "OD"),
            lignes=lignes,
            exercice=exercice,
            user=user,
        )

        return solde_init
