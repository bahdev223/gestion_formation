from datetime import timedelta
from math import ceil

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Abonnement


def expiring_subscription_alerts(days=7, overdue_days=7):
    now = timezone.now()
    subscriptions = (
        Abonnement.objects.filter(
            statut__in=[Abonnement.Statut.ACTIF, Abonnement.Statut.ESSAI],
            date_fin__gte=now - timedelta(days=overdue_days),
            date_fin__lte=now + timedelta(days=days),
        )
        .select_related("organisation", "plan")
        .order_by("date_fin")
    )
    alerts = []
    for subscription in subscriptions:
        seconds = (subscription.date_fin - now).total_seconds()
        alerts.append(
            {
                "abonnement": subscription,
                "jours_restants": ceil(seconds / 86400),
                "expire": seconds < 0,
            }
        )
    return alerts


class FeatureService:
    @staticmethod
    def _normalize_feature_key(feature_code):
        if not feature_code:
            return ()

        variants = {
            feature_code,
            feature_code.lower(),
            feature_code.upper(),
        }
        if "_" in feature_code:
            variants.add(feature_code.replace("_", ""))
            variants.add(feature_code.replace("_", "").lower())
            variants.add(feature_code.replace("_", "").upper())
            variants.add(feature_code.replace("_", "-").lower())
            variants.add(feature_code.replace("_", "-").upper())
        # Compatibilité spécifique avec certains anciens contenus
        if feature_code.lower() == "hr":
            variants.update({"rh", "RH", "ressources_humaines", "ressources-humaines"})
        if feature_code.lower() == "payroll":
            variants.update(
                {
                    "paye",
                    "PAIEMENT",
                    "paie",
                    "PAIE",
                    "paye",
                    "payroll_module",
                    "payrollmodule",
                    "rh_payroll",
                }
            )
        if feature_code.lower() == "accounting":
            variants.update({"comptabilite", "comptabilite_ohada", "accounting_module"})
        if feature_code.lower() == "treasury":
            variants.update({"tresorerie", "finance", "finance_module"})
        return tuple(variants)

    @staticmethod
    def _feature_enabled(plan, feature_code):
        fonctionnalites = plan.fonctionnalites if plan is not None else {}
        for key in FeatureService._normalize_feature_key(feature_code):
            if bool(fonctionnalites.get(key)):
                return True
        return False

    @staticmethod
    def has_feature(organisation, feature_code):
        from platform_admin.models import FeatureFlag

        platform_flag = FeatureFlag.objects.filter(code=feature_code).first()
        if platform_flag and platform_flag.is_enabled_for(organisation):
            return True
        abonnement = getattr(organisation, "abonnement", None)
        if abonnement is None or not abonnement.is_active:
            return False
        return FeatureService._feature_enabled(abonnement.plan, feature_code)

    @staticmethod
    def require_feature(organisation, feature_code):
        if not FeatureService.has_feature(organisation, feature_code):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied(
                "Cette fonctionnalite necessite un abonnement superieur."
            )


class QuotaService:
    @staticmethod
    def _plan(organisation):
        abonnement = getattr(organisation, "abonnement", None)
        if abonnement is None or not abonnement.is_active:
            return None
        return abonnement.plan

    @staticmethod
    def _file_size(field_file):
        if not field_file:
            return 0
        try:
            return field_file.size
        except (FileNotFoundError, OSError, ValueError):
            return 0

    @staticmethod
    def storage_bytes(organisation):
        from dashboard.models import ConfigurationOrganisation
        from documents.models import Attestation, DocumentGenere
        from formations.models import Formation
        from participants.models import DocumentParticipant, Participant

        total = QuotaService._file_size(organisation.logo)
        total += sum(
            QuotaService._file_size(member.user.photo)
            for member in organisation.membres.filter(
                is_active=True
            ).select_related("user")
        )
        for config in ConfigurationOrganisation.objects.filter(
            organisation=organisation
        ):
            total += sum(
                QuotaService._file_size(getattr(config, field))
                for field in ("logo", "signature_image", "cachet_image")
            )
        total += sum(
            QuotaService._file_size(item.image)
            for item in Formation.objects.filter(
                organisation=organisation
            ).only("image")
        )
        total += sum(
            QuotaService._file_size(item.photo)
            for item in Participant.objects.filter(
                organisation=organisation
            ).only("photo")
        )
        total += sum(
            QuotaService._file_size(item.fichier)
            for item in DocumentParticipant.objects.filter(
                organisation=organisation
            ).only("fichier")
        )
        total += sum(
            QuotaService._file_size(item.fichier_pdf)
            for item in Attestation.objects.filter(
                organisation=organisation
            ).only("fichier_pdf")
        )
        total += sum(
            QuotaService._file_size(item.fichier)
            for item in DocumentGenere.objects.filter(
                organisation=organisation
            ).only("fichier")
        )
        return total

    @staticmethod
    def usage(organisation):
        from formations.models import Formation
        from participants.models import Participant

        plan = QuotaService._plan(organisation)
        if not plan:
            return {}
        return {
            "utilisateurs": {
                "used": organisation.membres.filter(is_active=True).count(),
                "limit": plan.max_utilisateurs,
            },
            "participants": {
                "used": Participant.objects.filter(
                    organisation=organisation
                ).count(),
                "limit": plan.max_participants,
            },
            "formations_actives": {
                "used": Formation.objects.filter(
                    organisation=organisation,
                    statut="ACTIVE"
                ).count(),
                "limit": plan.max_formations_actives,
            },
            "stockage_mo": {
                "used": round(
                    QuotaService.storage_bytes(organisation)
                    / (1024 * 1024),
                    2,
                ),
                "limit": plan.max_stockage_mo,
            },
        }

    @staticmethod
    def can_add_user(organisation):
        usage = QuotaService.usage(organisation).get("utilisateurs")
        return bool(usage and usage["used"] < usage["limit"])

    @staticmethod
    def can_add_participant(organisation):
        usage = QuotaService.usage(organisation).get("participants")
        return bool(usage and usage["used"] < usage["limit"])

    @staticmethod
    def can_add_active_formation(organisation):
        usage = QuotaService.usage(organisation).get("formations_actives")
        return bool(usage and usage["used"] < usage["limit"])

    @staticmethod
    def can_store_bytes(organisation, additional_bytes):
        plan = QuotaService._plan(organisation)
        if not plan:
            return False
        limit_bytes = plan.max_stockage_mo * 1024 * 1024
        return (
            QuotaService.storage_bytes(organisation)
            + max(int(additional_bytes or 0), 0)
            <= limit_bytes
        )

    @staticmethod
    def require_participant_slot(organisation):
        if not QuotaService.can_add_participant(organisation):
            raise ValidationError(
                "Le quota de participants de votre offre est atteint."
            )

    @staticmethod
    def require_user_slot(organisation):
        if not QuotaService.can_add_user(organisation):
            raise ValidationError(
                "Le quota d'utilisateurs de votre offre est atteint."
            )

    @staticmethod
    def require_active_formation_slot(organisation):
        if not QuotaService.can_add_active_formation(organisation):
            raise ValidationError(
                "Le quota de formations actives de votre offre est atteint."
            )

    @staticmethod
    def require_storage(organisation, additional_bytes):
        if not QuotaService.can_store_bytes(organisation, additional_bytes):
            raise ValidationError(
                "Le quota de stockage de votre offre serait dépassé."
            )
