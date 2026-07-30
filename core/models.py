from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OrganisationOwnedModel(models.Model):
    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class AuditLog(OrganisationOwnedModel, TimeStampedModel):
    class Action(models.TextChoices):
        CREATE = "CREATE", "Creation"
        UPDATE = "UPDATE", "Modification"
        DELETE = "DELETE", "Suppression"
        CANCEL = "CANCEL", "Annulation"
        LOGIN = "LOGIN", "Connexion"
        LOGOUT = "LOGOUT", "Deconnexion"
        GENERATE = "GENERATE", "Generation"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    model_name = models.CharField(max_length=150)
    object_id = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
