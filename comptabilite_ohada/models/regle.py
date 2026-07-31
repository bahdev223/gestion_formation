from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import OrganisationOwnedModel


class TypeOperationComptable(models.TextChoices):
    """Evenements metier que le moteur sait comptabiliser.

    Chaque valeur correspond a une regle : c'est le pivot entre l'operation
    telle que la vit l'entreprise et les comptes du plan SYSCOHADA.
    """

    ENCAISSEMENT = "ENCAISSEMENT", _("Encaissement")
    DECAISSEMENT = "DECAISSEMENT", _("Décaissement")
    TRANSFERT = "TRANSFERT", _("Transfert entre comptes")
    ANNULATION_ENCAISSEMENT = "ANNULATION_ENCAISSEMENT", _("Annulation d'encaissement")
    ANNULATION_DECAISSEMENT = "ANNULATION_DECAISSEMENT", _("Annulation de décaissement")
    DEPOT_BANQUE = "DEPOT_BANQUE", _("Dépôt en banque")
    RETRAIT_BANQUE = "RETRAIT_BANQUE", _("Retrait de banque")
    FACTURE_CLIENT = "FACTURE_CLIENT", _("Facture client")
    PAIEMENT_CLIENT = "PAIEMENT_CLIENT", _("Paiement client")
    FACTURE_FOURNISSEUR = "FACTURE_FOURNISSEUR", _("Facture fournisseur")
    PAIEMENT_FOURNISSEUR = "PAIEMENT_FOURNISSEUR", _("Paiement fournisseur")
    SALAIRE = "SALAIRE", _("Salaire")


class RegleComptable(OrganisationOwnedModel, models.Model):
    """Correspondance configurable entre un evenement metier et ses comptes.

    Les comptes etaient ecrits en dur dans le code (« 706 » pour un
    encaissement, « 658 » pour un decaissement), ce qui obligeait a modifier
    le code pour adapter le plan comptable d'un client. Ils sont desormais
    portes par cette table, modifiable par entreprise.

    Un code de compte laisse vide signifie « fourni par l'operation » : lors
    d'un encaissement par exemple, le compte debite est celui de la caisse ou
    du compte bancaire reellement mouvemente, connu seulement a l'execution.
    """

    type_operation = models.CharField(
        _("Type d'opération"),
        max_length=40,
        choices=TypeOperationComptable.choices,
        db_index=True,
    )
    libelle = models.CharField(_("Libellé"), max_length=150, blank=True)
    compte_debit = models.CharField(
        _("Compte débité"),
        max_length=20,
        blank=True,
        help_text=_("Laisser vide si le compte est fourni par l'opération."),
    )
    compte_credit = models.CharField(
        _("Compte crédité"),
        max_length=20,
        blank=True,
        help_text=_("Laisser vide si le compte est fourni par l'opération."),
    )
    journal_code = models.CharField(_("Journal"), max_length=10, default="OD")
    actif = models.BooleanField(_("Active"), default=True, db_index=True)

    class Meta:
        verbose_name = _("Règle comptable")
        verbose_name_plural = _("Règles comptables")
        ordering = ["type_operation"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "type_operation"],
                name="unique_regle_par_organisation",
            )
        ]

    def __str__(self):
        return f"{self.get_type_operation_display()} : {self.compte_debit or '—'} / {self.compte_credit or '—'}"
