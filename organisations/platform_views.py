from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.utils import timezone

from organisations.forms import OrganisationSignupForm
from organisations.services.signup_service import create_organisation_account
from organisations.utils import get_user_default_organisation
from platform_admin.access import get_platform_role
from subscriptions.models import PlanAbonnement


def landing_page(request):
    if request.user.is_authenticated:
        if get_platform_role(request.user):
            return redirect("/platform/")
        organisation = get_user_default_organisation(request.user)
        if organisation is not None:
            return redirect(f"/o/{organisation.slug}/dashboard/")
    plans = PlanAbonnement.objects.filter(is_active=True).order_by("ordre", "prix_mensuel")
    return render(request, "platform/landing.html", {"plans": plans})


def create_organisation(request):
    if request.user.is_authenticated:
        if get_platform_role(request.user):
            return redirect("/platform/")
        organisation = get_user_default_organisation(request.user)
        if organisation is not None:
            return redirect(f"/o/{organisation.slug}/dashboard/")

    from platform_admin.models import MaintenanceWindow

    now = timezone.now()
    signup_blocked = MaintenanceWindow.objects.filter(
        bloque_inscriptions=True,
        statut__in=[
            MaintenanceWindow.Statut.PLANIFIEE,
            MaintenanceWindow.Statut.EN_COURS,
        ],
        starts_at__lte=now,
        ends_at__gte=now,
    ).exists()
    form = OrganisationSignupForm(request.POST or None)
    if request.method == "POST" and signup_blocked:
        messages.error(
            request,
            "Les créations d’entreprise sont temporairement suspendues pour maintenance.",
        )
        return render(
            request,
            "platform/create_organisation.html",
            {"form": form, "signup_blocked": True},
            status=503,
        )
    if request.method == "POST" and form.is_valid():
        organisation, user = create_organisation_account(form.cleaned_data)
        login(request, user, backend="accounts.authentication.EmailOrMatriculeBackend")
        from platform_admin.models import PlatformAuditEvent
        from platform_admin.services import log_platform_event

        log_platform_event(
            request,
            PlatformAuditEvent.Type.ORGANISATION_CREATED,
            f"Organisation {organisation.nom} créée depuis l’inscription publique.",
            organisation=organisation,
            object_type="Organisation",
            object_id=organisation.pk,
        )
        return redirect(f"/o/{organisation.slug}/dashboard/")

    return render(
        request,
        "platform/create_organisation.html",
        {"form": form, "signup_blocked": signup_blocked},
    )
