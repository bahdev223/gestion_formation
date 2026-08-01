from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from .access import require_member_permission
from .models import Organisation


class CurrentOrganisationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organisation = None
        request.organisation_member = None

        parts = [part for part in request.path_info.split("/") if part]
        if len(parts) >= 2 and parts[0] == "o":
            organisation = get_object_or_404(Organisation, slug=parts[1])
            request.organisation = organisation
            if request.user.is_authenticated:
                member = organisation.membres.filter(
                    user=request.user,
                    is_active=True,
                ).first()
                if not member and not request.user.is_superuser:
                    raise PermissionDenied(
                        "Vous n'avez pas acces a cette organisation."
                    )
                request.organisation_member = member

        return self.get_response(request)


class TenantRoleAccessMiddleware:
    """Applique les permissions du membre dans l'entreprise courante.

    Les permissions Django historiques restent compatibles, mais cette couche
    empeche qu'un role global plus large ouvre des actions dans un autre tenant.
    """

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    def __init__(self, get_response):
        self.get_response = get_response

    def required_permission(self, request):
        organisation = getattr(request, "organisation", None)
        if organisation is None or not request.user.is_authenticated:
            return None
        prefix = f"/o/{organisation.slug}/"
        relative = request.path_info.removeprefix(prefix).strip("/")
        safe = request.method in self.SAFE_METHODS

        if relative.startswith("parametres-utilisateurs"):
            return "users.manage"
        if relative.startswith("parametres-entreprise"):
            return "settings.manage"
        if relative.startswith("ressources-humaines"):
            return "rh.manage"
        if relative.startswith("paie-salariale"):
            return "payroll.manage"
        if relative.startswith("comptabilite"):
            return "accounting.manage"
        if relative.startswith("comptes-financiers"):
            if safe:
                return "finance.view"
            if "mouvements/encaisser" in relative:
                return "finance.collect"
            if "mouvements/decaisser" in relative or "transfert" in relative:
                return "finance.disburse"
            return "accounting.manage"
        if relative.startswith("paiements"):
            return "finance.view" if safe else "finance.collect"
        if relative.startswith("operations"):
            return "finance.view" if safe else "accounting.manage"
        if not safe and relative.startswith(("formations", "presences", "documents")):
            return "formations.manage"
        if not safe and relative.startswith(("participants", "inscriptions")):
            return "participants.manage"
        return None

    def __call__(self, request):
        permission = self.required_permission(request)
        if permission:
            require_member_permission(request, permission)
        return self.get_response(request)
