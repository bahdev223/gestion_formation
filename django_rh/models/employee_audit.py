from django.conf import settings
from django.db import models

from core.models import OrganisationOwnedModel


class EmployeeAuditLog(OrganisationOwnedModel, models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Création"
        HIRE = "hire", "Embauche"
        SUSPEND = "suspend", "Suspension"
        PROMOTE = "promote", "Promotion"
        TRANSFER = "transfer", "Transfert"
        TERMINATE = "terminate", "Fin de contrat"

    employee = models.ForeignKey("rh.Employee", on_delete=models.CASCADE, related_name="audit_logs")
    action = models.CharField(max_length=50, choices=Action.choices)
    details = models.JSONField(null=True, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        verbose_name = "Audit employé"
        verbose_name_plural = "Audits employés"
        ordering = ["-performed_at"]
