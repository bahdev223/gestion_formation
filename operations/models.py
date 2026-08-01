from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import OrganisationOwnedModel, TimeStampedModel

from .catalogue import obtenir


class Operation(OrganisationOwnedModel, TimeStampedModel):
    """Evenement metier declare par l'entreprise.

    C'est le point d'entree du logiciel : l'utilisateur decrit ce qui s'est
    passe (une depense, un encaissement, une facture) et le moteur en deduit
    l'ecriture comptable. Les debits et credits ne sont jamais saisis ici.
    """

    class Statut(models.TextChoices):
        BROUILLON = "BROUILLON", _("Brouillon")
        VALIDEE = "VALIDEE", _("Validée")
        ANNULEE = "ANNULEE", _("Annulée")

    numero = models.CharField(_("Numéro"), max_length=30, db_index=True)
    date_operation = models.DateField(_("Date"), db_index=True)
    type_operation = models.CharField(
        _("Type d'opération"), max_length=40, db_index=True
    )
    description = models.CharField(_("Description"), max_length=255)
    montant = models.DecimalField(_("Montant"), max_digits=14, decimal_places=2)
    devise = models.CharField(_("Devise"), max_length=10, default="FCFA")
    statut = models.CharField(
        _("Statut"),
        max_length=20,
        choices=Statut.choices,
        default=Statut.BROUILLON,
        db_index=True,
    )

    # Champs supplementaires propres au type d'operation (beneficiaire, motif,
    # numero de piece, TVA...). Stockes ainsi pour qu'ajouter un type ne
    # demande pas de migration.
    donnees = models.JSONField(_("Données"), default=dict, blank=True)

    justificatif = models.FileField(
        _("Justificatif"),
        upload_to="operations/justificatifs/",
        null=True,
        blank=True,
    )

    compte_tresorerie = models.ForeignKey(
        "comptes.Compte",
        verbose_name=_("Compte de trésorerie"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="operations",
    )
    compte_destination = models.ForeignKey(
        "comptes.Compte",
        verbose_name=_("Compte de destination"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="operations_recues",
    )

    # Axes d'analyse (classe 9) : permettent de suivre la marge d'un projet ou
    # d'une formation sans creer de comptes dedies.
    centre_cout = models.CharField(_("Centre de coût"), max_length=100, blank=True)
    projet = models.CharField(_("Projet"), max_length=100, blank=True)

    ecriture = models.OneToOneField(
        "comptabilite_ohada.EcritureComptable",
        verbose_name=_("Écriture générée"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operation",
    )
    mouvement = models.ForeignKey(
        "comptes.MouvementCompte",
        verbose_name=_("Mouvement financier"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operations",
    )

    module_source = models.CharField(
        _("Module d'origine"),
        max_length=50,
        blank=True,
        help_text=_("Renseigné quand l'opération est créée par un autre module."),
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operations_creees",
    )
    validee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operations_validees",
    )
    validee_le = models.DateTimeField(_("Validée le"), null=True, blank=True)
    motif_annulation = models.TextField(_("Motif d'annulation"), blank=True)

    class Meta:
        verbose_name = _("Opération")
        verbose_name_plural = _("Opérations")
        ordering = ["-date_operation", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "numero"],
                name="unique_numero_operation_par_organisation",
            )
        ]

    def __str__(self):
        return f"{self.numero} · {self.libelle_type} · {self.montant}"

    @property
    def definition(self):
        """Definition catalogue du type, ou None si le type a disparu."""
        return obtenir(self.type_operation)

    @property
    def libelle_type(self):
        definition = self.definition
        return definition.libelle if definition else self.type_operation

    @property
    def classe(self):
        definition = self.definition
        return definition.classe if definition else ""

    @property
    def classe_libelle(self):
        definition = self.definition
        return definition.classe_libelle if definition else ""

    @property
    def est_modifiable(self):
        return self.statut == self.Statut.BROUILLON

    @property
    def est_comptabilisee(self):
        return self.ecriture_id is not None
