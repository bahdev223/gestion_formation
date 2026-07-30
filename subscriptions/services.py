class FeatureService:
    @staticmethod
    def has_feature(organisation, feature_code):
        from platform_admin.models import FeatureFlag

        platform_flag = FeatureFlag.objects.filter(code=feature_code).first()
        if platform_flag and platform_flag.is_enabled_for(organisation):
            return True
        abonnement = getattr(organisation, "abonnement", None)
        if abonnement is None or not abonnement.is_active:
            return False
        return bool(abonnement.plan.fonctionnalites.get(feature_code, False))

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
        return abonnement.plan if abonnement else None

    @staticmethod
    def usage(organisation):
        plan = QuotaService._plan(organisation)
        if not plan:
            return {}
        return {
            "utilisateurs": {
                "used": organisation.membres.filter(is_active=True).count(),
                "limit": plan.max_utilisateurs,
            },
            "participants": {
                "used": getattr(organisation, "participants", []).count()
                if hasattr(organisation, "participants")
                else 0,
                "limit": plan.max_participants,
            },
            "formations_actives": {
                "used": getattr(organisation, "formations", []).filter(
                    statut="ACTIVE"
                ).count()
                if hasattr(organisation, "formations")
                else 0,
                "limit": plan.max_formations_actives,
            },
            "stockage_mo": {
                "used": 0,
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
