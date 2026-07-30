from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import OrganisationOwnedModel


class Employee(OrganisationOwnedModel, models.Model):
    class Status(models.TextChoices):
        RECRUITED = "recruited", _("Recruté")
        ACTIVE = "active", _("Actif")
        SUSPENDED = "suspended", _("Suspendu")
        TERMINATED = "terminated", _("Fin de contrat")
        ARCHIVED = "archived", _("Archivé")

    class Sex(models.TextChoices):
        M = "M", _("Masculin")
        F = "F", _("Féminin")

    class ContractType(models.TextChoices):
        CDI = "CDI", _("CDI")
        CDD = "CDD", _("CDD")
        INTERNSHIP = "internship", _("Stage")
        CONSULTANT = "consultant", _("Consultant")

    matricule = models.CharField(max_length=20, unique=True, verbose_name="Matricule")
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    sex = models.CharField(max_length=1, choices=Sex.choices, default=Sex.M, verbose_name="Sexe")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Date de naissance")
    phone = models.CharField(max_length=30, blank=True, verbose_name="Téléphone")
    email = models.EmailField(blank=True, verbose_name="Email")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECRUITED, verbose_name="Statut")
    department = models.ForeignKey(
        "rh.Department", null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Département",
    )
    position = models.ForeignKey(
        "rh.Position", null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Poste",
    )
    contract_type = models.CharField(max_length=20, choices=ContractType.choices, default=ContractType.CDI, verbose_name="Type de contrat")
    hire_date = models.DateField(null=True, blank=True, verbose_name="Date d'embauche")
    termination_date = models.DateField(null=True, blank=True, verbose_name="Date de fin")
    salaire_mensuel = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="Salaire mensuel",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Employé"
        verbose_name_plural = "Employés"
        ordering = ["-created_at"]
        permissions = [
            ("rh_create", "Can create employees"),
            ("rh_edit", "Can edit employees"),
            ("rh_delete", "Can delete employees"),
            ("rh_view", "Can view employees"),
            ("rh_promote", "Can promote employees"),
            ("rh_transfer", "Can transfer employees"),
            ("rh_terminate", "Can terminate employees"),
        ]

    def __str__(self):
        return f"{self.matricule} - {self.first_name} {self.last_name}"
