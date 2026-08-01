"""Catalogue des operations metier.

L'utilisateur ne saisit pas des debits et des credits : il declare ce qui
s'est passe dans l'entreprise. Ce catalogue est le pivot entre ce vocabulaire
metier et la comptabilite.

Il est declaratif volontairement : ajouter un type d'operation ne demande ni
migration ni modification de vue. Chaque definition indique la classe
SYSCOHADA concernee, la regle comptable a appliquer, le sens du flux et les
champs supplementaires que le formulaire doit presenter.
"""

from dataclasses import dataclass, field

from comptabilite_ohada.models import TypeOperationComptable


class ClasseOperation:
    """Les neuf classes du plan comptable SYSCOHADA."""

    FINANCEMENT = "1"
    IMMOBILISATIONS = "2"
    STOCKS = "3"
    TIERS = "4"
    TRESORERIE = "5"
    CHARGES = "6"
    PRODUITS = "7"
    RESULTAT = "8"
    ANALYTIQUE = "9"

    LIBELLES = {
        FINANCEMENT: "Financement et capitaux",
        IMMOBILISATIONS: "Immobilisations",
        STOCKS: "Stocks",
        TIERS: "Tiers",
        TRESORERIE: "Trésorerie",
        CHARGES: "Charges",
        PRODUITS: "Produits",
        RESULTAT: "Résultat",
        ANALYTIQUE: "Comptabilité analytique",
    }

    # La classe 8 est generee par la cloture, l'utilisateur n'y touche pas.
    # La classe 9 est un axe d'analyse, pas un type d'operation.
    SAISISSABLES = (
        TRESORERIE,
        CHARGES,
        PRODUITS,
        TIERS,
        IMMOBILISATIONS,
        STOCKS,
        FINANCEMENT,
    )


class SensFlux:
    ENTREE = "ENTREE"
    SORTIE = "SORTIE"
    NEUTRE = "NEUTRE"


@dataclass(frozen=True)
class DefinitionOperation:
    """Description d'un type d'operation saisissable."""

    code: str
    libelle: str
    classe: str
    regle: str
    sens: str
    # Champs supplementaires demandes en plus du socle commun (date, montant,
    # description, justificatif). C'est ce qui fait varier le formulaire.
    champs: tuple = field(default=())
    # Un compte de tresorerie est-il necessaire pour executer l'operation ?
    exige_compte_tresorerie: bool = True
    aide: str = ""

    @property
    def classe_libelle(self):
        return ClasseOperation.LIBELLES.get(self.classe, self.classe)


def _definir(*definitions):
    return {definition.code: definition for definition in definitions}


# Sous-ensemble couvert aujourd'hui : les types pour lesquels une regle
# comptable existe. Le catalogue est concu pour s'etendre sans refonte.
CATALOGUE = _definir(
    # ─── Classe 5 : Trésorerie ────────────────────────────────
    DefinitionOperation(
        code="ENCAISSEMENT",
        libelle="Encaissement",
        classe=ClasseOperation.TRESORERIE,
        regle=TypeOperationComptable.ENCAISSEMENT,
        sens=SensFlux.ENTREE,
        champs=("compte_tresorerie", "reference_externe"),
        aide="Entrée d'argent en caisse, en banque ou par paiement mobile.",
    ),
    DefinitionOperation(
        code="DECAISSEMENT",
        libelle="Décaissement",
        classe=ClasseOperation.TRESORERIE,
        regle=TypeOperationComptable.DECAISSEMENT,
        sens=SensFlux.SORTIE,
        champs=("compte_tresorerie", "reference_externe"),
        aide="Sortie d'argent non rattachée à une facture fournisseur.",
    ),
    DefinitionOperation(
        code="TRANSFERT",
        libelle="Transfert entre comptes",
        classe=ClasseOperation.TRESORERIE,
        regle=TypeOperationComptable.TRANSFERT,
        sens=SensFlux.NEUTRE,
        champs=("compte_tresorerie", "compte_destination"),
        aide="Virement interne : caisse vers banque, banque vers mobile money…",
    ),
    DefinitionOperation(
        code="DEPOT_BANQUE",
        libelle="Dépôt en banque",
        classe=ClasseOperation.TRESORERIE,
        regle=TypeOperationComptable.DEPOT_BANQUE,
        sens=SensFlux.NEUTRE,
        champs=("compte_tresorerie",),
    ),
    DefinitionOperation(
        code="RETRAIT_BANQUE",
        libelle="Retrait de banque",
        classe=ClasseOperation.TRESORERIE,
        regle=TypeOperationComptable.RETRAIT_BANQUE,
        sens=SensFlux.NEUTRE,
        champs=("compte_tresorerie",),
    ),
    # ─── Classe 6 : Charges ───────────────────────────────────
    DefinitionOperation(
        code="CHARGE_LOYER",
        libelle="Loyer",
        classe=ClasseOperation.CHARGES,
        regle=TypeOperationComptable.DECAISSEMENT,
        sens=SensFlux.SORTIE,
        champs=("compte_tresorerie", "beneficiaire", "periode_concernee",
                "centre_cout", "projet"),
    ),
    DefinitionOperation(
        code="CHARGE_TRANSPORT",
        libelle="Transport et carburant",
        classe=ClasseOperation.CHARGES,
        regle=TypeOperationComptable.DECAISSEMENT,
        sens=SensFlux.SORTIE,
        champs=("compte_tresorerie", "beneficiaire", "motif", "centre_cout",
                "projet"),
        aide="Déplacements, carburant, entretien de véhicule.",
    ),
    DefinitionOperation(
        code="CHARGE_UTILITES",
        libelle="Électricité, eau, internet",
        classe=ClasseOperation.CHARGES,
        regle=TypeOperationComptable.DECAISSEMENT,
        sens=SensFlux.SORTIE,
        champs=("compte_tresorerie", "beneficiaire", "periode_concernee",
                "centre_cout"),
    ),
    DefinitionOperation(
        code="CHARGE_DIVERSE",
        libelle="Autre charge",
        classe=ClasseOperation.CHARGES,
        regle=TypeOperationComptable.DECAISSEMENT,
        sens=SensFlux.SORTIE,
        champs=("compte_tresorerie", "beneficiaire", "motif", "centre_cout",
                "projet"),
    ),
    # ─── Classe 7 : Produits ──────────────────────────────────
    DefinitionOperation(
        code="VENTE",
        libelle="Vente ou prestation",
        classe=ClasseOperation.PRODUITS,
        regle=TypeOperationComptable.ENCAISSEMENT,
        sens=SensFlux.ENTREE,
        champs=("compte_tresorerie", "tiers", "centre_cout", "projet"),
    ),
    DefinitionOperation(
        code="RECETTE_FORMATION",
        libelle="Recette de formation",
        classe=ClasseOperation.PRODUITS,
        regle=TypeOperationComptable.ENCAISSEMENT,
        sens=SensFlux.ENTREE,
        champs=("compte_tresorerie", "tiers", "projet"),
        aide="Encaissement rattaché à une formation ou une session.",
    ),
    # ─── Classe 4 : Tiers ─────────────────────────────────────
    DefinitionOperation(
        code="FACTURE_FOURNISSEUR",
        libelle="Facture fournisseur",
        classe=ClasseOperation.TIERS,
        regle=TypeOperationComptable.FACTURE_FOURNISSEUR,
        sens=SensFlux.NEUTRE,
        champs=("tiers", "numero_piece", "date_echeance", "montant_tva",
                "centre_cout", "projet"),
        exige_compte_tresorerie=False,
        aide="Enregistre la dette. Le paiement est une opération distincte.",
    ),
    DefinitionOperation(
        code="PAIEMENT_FOURNISSEUR",
        libelle="Paiement fournisseur",
        classe=ClasseOperation.TIERS,
        regle=TypeOperationComptable.PAIEMENT_FOURNISSEUR,
        sens=SensFlux.SORTIE,
        champs=("compte_tresorerie", "tiers", "numero_piece"),
    ),
    DefinitionOperation(
        code="FACTURE_CLIENT",
        libelle="Facture client",
        classe=ClasseOperation.TIERS,
        regle=TypeOperationComptable.FACTURE_CLIENT,
        sens=SensFlux.NEUTRE,
        champs=("tiers", "numero_piece", "date_echeance", "montant_tva",
                "centre_cout", "projet"),
        exige_compte_tresorerie=False,
        aide="Enregistre la créance. L'encaissement est une opération distincte.",
    ),
    DefinitionOperation(
        code="PAIEMENT_CLIENT",
        libelle="Paiement client",
        classe=ClasseOperation.TIERS,
        regle=TypeOperationComptable.PAIEMENT_CLIENT,
        sens=SensFlux.ENTREE,
        champs=("compte_tresorerie", "tiers", "numero_piece"),
    ),
)


def definitions_par_classe():
    """Catalogue regroupe par classe, dans l'ordre de saisie courant."""
    groupes = []
    for classe in ClasseOperation.SAISISSABLES:
        types = [d for d in CATALOGUE.values() if d.classe == classe]
        if types:
            groupes.append(
                {
                    "classe": classe,
                    "libelle": ClasseOperation.LIBELLES[classe],
                    "types": sorted(types, key=lambda d: d.libelle),
                }
            )
    return groupes


def obtenir(code):
    """Definition d'un type d'operation, ou None si inconnu."""
    return CATALOGUE.get(code)


def codes_valides():
    return tuple(CATALOGUE)


def choix_types():
    """Couples (code, libelle) groupes par classe, pour un champ de formulaire."""
    return [
        (
            groupe["libelle"],
            [(d.code, d.libelle) for d in groupe["types"]],
        )
        for groupe in definitions_par_classe()
    ]
