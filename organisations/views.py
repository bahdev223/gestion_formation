from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from subscriptions.services import QuotaService


@login_required
def owner_dashboard(request, organisation_slug):
    organisation = request.organisation
    abonnement = getattr(organisation, "abonnement", None)
    return render(
        request,
        "organisations/owner_dashboard.html",
        {
            "organisation": organisation,
            "abonnement": abonnement,
            "quota_usage": QuotaService.usage(organisation),
        },
    )
