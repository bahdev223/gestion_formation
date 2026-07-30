from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from subscriptions.models import PaiementAbonnement

from .models import PlatformAuditEvent, SaaSInvoice
from .services import get_client_ip


@receiver(user_logged_in)
def audit_successful_login(sender, request, user, **kwargs):
    organisation = getattr(request, "organisation", None) if request else None
    PlatformAuditEvent.objects.create(
        organisation=organisation,
        acteur=user,
        type_evenement=PlatformAuditEvent.Type.LOGIN,
        description=f"Connexion réussie de {user.get_username()}.",
        adresse_ip=get_client_ip(request) if request else None,
        objet_type="User",
        objet_id=str(user.pk),
    )


@receiver(user_login_failed)
def audit_failed_login(sender, credentials, request, **kwargs):
    identifier = credentials.get("username") or credentials.get("email") or "inconnu"
    PlatformAuditEvent.objects.create(
        type_evenement=PlatformAuditEvent.Type.LOGIN_FAILED,
        severite=PlatformAuditEvent.Severite.WARNING,
        description=f"Tentative de connexion échouée pour {identifier}.",
        adresse_ip=get_client_ip(request) if request else None,
        metadata={"identifier": str(identifier)[:150]},
    )


@receiver(post_save, sender=PaiementAbonnement)
def create_invoice_for_valid_payment(sender, instance, **kwargs):
    if instance.statut != PaiementAbonnement.Statut.VALIDE:
        return
    SaaSInvoice.objects.get_or_create(
        paiement=instance,
        defaults={
            "organisation": instance.abonnement.organisation,
            "abonnement": instance.abonnement,
            "montant_ht": instance.montant,
            "taxes": 0,
            "montant_ttc": instance.montant,
            "date_emission": timezone.localdate(),
            "date_echeance": timezone.localdate(),
            "statut": SaaSInvoice.Statut.PAYEE,
        },
    )
