from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

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
