from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from organisations.models import MembreOrganisation
from platform_admin.models import PlatformAuditEvent
from subscriptions.services import expiring_subscription_alerts


class Command(BaseCommand):
    help = "Envoie les alertes d’échéance d’abonnement aux propriétaires."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les alertes sans envoyer d’email.",
        )

    def handle(self, *args, **options):
        sent = 0
        skipped = 0
        thresholds = {7, 3, 1, 0}
        alerts = expiring_subscription_alerts(days=max(thresholds), overdue_days=0)
        for alert in alerts:
            days_remaining = alert["jours_restants"]
            if days_remaining not in thresholds:
                continue
            subscription = alert["abonnement"]
            owner = (
                subscription.organisation.membres.select_related("user")
                .filter(
                    role=MembreOrganisation.Role.PROPRIETAIRE,
                    is_active=True,
                    user__is_active=True,
                )
                .first()
            )
            if not owner or not owner.user.email:
                skipped += 1
                continue

            alert_key = (
                f"{subscription.pk}:{subscription.date_fin.date()}:{days_remaining}"
            )
            already_sent = PlatformAuditEvent.objects.filter(
                type_evenement=PlatformAuditEvent.Type.SUBSCRIPTION,
                objet_type="SubscriptionExpiryAlert",
                objet_id=alert_key,
            ).exists()
            if already_sent:
                skipped += 1
                continue

            if days_remaining == 0:
                timing = "expire aujourd’hui"
            else:
                timing = f"expire dans {days_remaining} jour(s)"
            self.stdout.write(
                f"{subscription.organisation.nom}: {timing} -> {owner.user.email}"
            )
            if options["dry_run"]:
                continue

            delivered = send_mail(
                subject=f"Abonnement {subscription.organisation.nom} : échéance proche",
                message=(
                    f"Bonjour {owner.user.get_full_name() or owner.user.username},\n\n"
                    f"Votre abonnement SahelTech {timing}, le "
                    f"{subscription.date_fin:%d/%m/%Y}.\n"
                    "Contactez l’équipe SahelTech pour enregistrer votre renouvellement "
                    "et éviter une interruption de service.\n\n"
                    f"Accès : {settings.PUBLIC_APP_URL}/accounts/login/"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[owner.user.email],
                fail_silently=False,
            )
            if delivered:
                PlatformAuditEvent.objects.create(
                    organisation=subscription.organisation,
                    type_evenement=PlatformAuditEvent.Type.SUBSCRIPTION,
                    description=(
                        f"Alerte d’échéance envoyée à {owner.user.email} "
                        f"({days_remaining} jour(s))."
                    ),
                    objet_type="SubscriptionExpiryAlert",
                    objet_id=alert_key,
                    metadata={"days_remaining": days_remaining},
                )
                sent += 1

        self.stdout.write(
            self.style.SUCCESS(f"Alertes envoyées : {sent} · ignorées : {skipped}")
        )
