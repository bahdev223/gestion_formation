"""Resolution des comptes a partir du type d'operation metier.

Point d'entree unique : plus aucun code de compte ne doit apparaitre dans une
vue, un signal ou une integration. Le moteur demande ici quels comptes
utiliser, et l'entreprise peut les redefinir sans toucher au code.
"""

from ..models import RegleComptable, TypeOperationComptable

# Valeurs de reference, utilisees tant qu'une organisation n'a pas sa propre
# regle. Elles reprennent exactement le comportement precedent, ce qui rend
# l'introduction des regles sans effet de bord : une entreprise sans regle
# enregistree continue de produire les memes ecritures qu'avant.
# Un compte vide signifie « fourni par l'operation » (compte de tresorerie
# reellement mouvemente, compte du tiers concerne...).
REGLES_PAR_DEFAUT = {
    TypeOperationComptable.ENCAISSEMENT: {
        "libelle": "Encaissement",
        "compte_debit": "",
        "compte_credit": "706",
        "journal_code": "VN",
    },
    TypeOperationComptable.DECAISSEMENT: {
        "libelle": "Décaissement",
        "compte_debit": "658",
        "compte_credit": "",
        "journal_code": "CS",
    },
    TypeOperationComptable.TRANSFERT: {
        "libelle": "Transfert entre comptes",
        "compte_debit": "",
        "compte_credit": "",
        "journal_code": "TR",
    },
    TypeOperationComptable.ANNULATION_ENCAISSEMENT: {
        "libelle": "Annulation d'encaissement",
        "compte_debit": "706",
        "compte_credit": "",
        "journal_code": "OD",
    },
    TypeOperationComptable.ANNULATION_DECAISSEMENT: {
        "libelle": "Annulation de décaissement",
        "compte_debit": "",
        "compte_credit": "658",
        "journal_code": "OD",
    },
    TypeOperationComptable.DEPOT_BANQUE: {
        "libelle": "Dépôt en banque",
        "compte_debit": "521",
        "compte_credit": "",
        "journal_code": "BQ",
    },
    TypeOperationComptable.RETRAIT_BANQUE: {
        "libelle": "Retrait de banque",
        "compte_debit": "",
        "compte_credit": "521",
        "journal_code": "BQ",
    },
    TypeOperationComptable.FACTURE_CLIENT: {
        "libelle": "Facture client",
        "compte_debit": "411",
        "compte_credit": "706",
        "journal_code": "VN",
    },
    TypeOperationComptable.PAIEMENT_CLIENT: {
        "libelle": "Paiement client",
        "compte_debit": "",
        "compte_credit": "411",
        "journal_code": "CS",
    },
    TypeOperationComptable.FACTURE_FOURNISSEUR: {
        "libelle": "Facture fournisseur",
        "compte_debit": "601",
        "compte_credit": "401",
        "journal_code": "AC",
    },
    TypeOperationComptable.PAIEMENT_FOURNISSEUR: {
        "libelle": "Paiement fournisseur",
        "compte_debit": "401",
        "compte_credit": "",
        "journal_code": "CS",
    },
    TypeOperationComptable.SALAIRE: {
        "libelle": "Salaire",
        "compte_debit": "661",
        "compte_credit": "422",
        "journal_code": "OD",
    },
}


class RegleComptableService:
    @staticmethod
    def resoudre(organisation, type_operation):
        """Renvoie les comptes et le journal a utiliser pour cette operation.

        Cherche d'abord une regle propre a l'organisation, puis retombe sur la
        valeur de reference. Le repli est volontaire : il garantit qu'une
        entreprise sans regle configuree reste fonctionnelle.
        """
        if organisation is None:
            raise ValueError(
                "Une organisation est obligatoire pour resoudre une regle "
                "comptable."
            )
        defaut = REGLES_PAR_DEFAUT.get(type_operation)
        if defaut is None:
            raise ValueError(f"Type d'operation inconnu : {type_operation!r}")

        regle = RegleComptable.objects.filter(
            organisation=organisation,
            type_operation=type_operation,
            actif=True,
        ).first()
        if regle is None:
            return dict(defaut)
        return {
            "libelle": regle.libelle or defaut["libelle"],
            "compte_debit": regle.compte_debit,
            "compte_credit": regle.compte_credit,
            "journal_code": regle.journal_code or defaut["journal_code"],
        }

    @staticmethod
    def compte_tresorerie_defaut(organisation):
        """Compte de caisse a utiliser quand l'operation n'en precise aucun.

        Lit ConfigurationComptable, qui portait deja ce reglage par
        entreprise mais que le code ignorait au profit d'un « 571 » litteral.
        """
        from ..models import ConfigurationComptable

        configuration = ConfigurationComptable.objects.filter(
            organisation=organisation
        ).first()
        if configuration and configuration.compte_caisse_defaut:
            return configuration.compte_caisse_defaut
        return "571"

    @staticmethod
    def initialiser(organisation, ecraser=False):
        """Cree les regles de reference pour une organisation.

        Sans ecraser=True, les regles deja personnalisees sont preservees.
        """
        creees = 0
        for type_operation, valeurs in REGLES_PAR_DEFAUT.items():
            regle, cree = RegleComptable.objects.get_or_create(
                organisation=organisation,
                type_operation=type_operation,
                defaults=valeurs,
            )
            if cree:
                creees += 1
            elif ecraser:
                for champ, valeur in valeurs.items():
                    setattr(regle, champ, valeur)
                regle.save(update_fields=list(valeurs))
        return creees
