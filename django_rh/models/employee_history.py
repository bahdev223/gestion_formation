from django.conf import settings
from django.db import models

from core.models import OrganisationOwnedModel


class EmployeeHistory(OrganisationOwnedModel, models.Model):
    employee = models.ForeignKey("rh.Employee", on_delete=models.CASCADE, related_name="history")
    action = models.CharField(max_length=50)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Historique employé"
        verbose_name_plural = "Historiques employés"
        ordering = ["-performed_at"]
