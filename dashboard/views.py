from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import UpdateView

from formations.models import Formation, SessionFormation
from inscriptions.models import Inscription
from organisations.utils import (
    get_request_organisation,
    get_user_default_organisation,
    tenant_reverse,
)
from paiements.models import Paiement
from participants.models import Participant

from .forms import ConfigurationOrganisationForm
from .models import ConfigurationOrganisation


@login_required
def dashboard_home(request, **kwargs):
    if getattr(request, "organisation", None) is None:
        organisation = get_user_default_organisation(request.user)
        if organisation is not None:
            return redirect(
                "organisations:owner-dashboard",
                organisation_slug=organisation.slug,
            )

    today = timezone.localdate()
    organisation = get_request_organisation(request)
    payments_qs = Paiement.objects.all()
    registrations_qs = Inscription.objects.all()
    sessions_qs = SessionFormation.objects.all()
    formations_qs = Formation.objects.all()
    participants_qs = Participant.objects.all()
    if organisation:
        payments_qs = payments_qs.filter(organisation=organisation)
        registrations_qs = registrations_qs.filter(organisation=organisation)
        sessions_qs = sessions_qs.filter(organisation=organisation)
        formations_qs = formations_qs.filter(organisation=organisation)
        participants_qs = participants_qs.filter(organisation=organisation)
    valid_payments = payments_qs.filter(statut=Paiement.Statut.VALIDE)
    active_registrations = registrations_qs.exclude(
        statut=Inscription.Statut.ANNULE
    )
    total_invoiced = (
        active_registrations.aggregate(total=Sum("montant_final"))["total"]
        or Decimal("0")
    )
    total_collected = (
        valid_payments.aggregate(total=Sum("montant"))["total"] or Decimal("0")
    )
    upcoming_sessions = (
        sessions_qs.filter(date_fin__gte=today)
        .exclude(statut=SessionFormation.Statut.ANNULEE)
        .select_related("formation", "formateur")
        .annotate(inscrits_count=Count("inscriptions"))
        .order_by("date_debut")[:5]
    )
    context = {
        "title": "Tableau de bord",
        "formations_actives": formations_qs.filter(
            statut=Formation.Statut.ACTIVE
        ).count(),
        "participants_count": participants_qs.count(),
        "sessions_planifiees": upcoming_sessions.count(),
        "inscriptions_count": active_registrations.count(),
        "encaissements_jour": valid_payments.filter(
            date_paiement__date=today
        ).aggregate(total=Sum("montant"))["total"]
        or Decimal("0"),
        "encaissements_mois": valid_payments.filter(
            date_paiement__year=today.year,
            date_paiement__month=today.month,
        ).aggregate(total=Sum("montant"))["total"]
        or Decimal("0"),
        "total_facture": total_invoiced,
        "total_encaisse": total_collected,
        "reste_global": max(total_invoiced - total_collected, Decimal("0")),
        "upcoming_sessions": upcoming_sessions,
        "recent_inscriptions": active_registrations.select_related(
            "participant", "session", "session__formation"
        ).order_by("-created_at")[:5],
        "recent_payments": valid_payments.select_related(
            "inscription", "inscription__participant"
        ).order_by("-date_paiement")[:5],
    }
    return render(request, "dashboard/index.html", context)


class ConfigurationOrganisationView(
    LoginRequiredMixin, SuccessMessageMixin, UpdateView
):
    model = ConfigurationOrganisation
    form_class = ConfigurationOrganisationForm
    template_name = "dashboard/organisation_form.html"
    def get_success_url(self):
        return tenant_reverse(self.request, "dashboard:organisation-settings")
    success_message = "Les paramètres de l’entreprise ont été enregistrés."

    def get_object(self, queryset=None):
        organisation = get_request_organisation(self.request)
        qs = ConfigurationOrganisation.objects.order_by("pk")
        if organisation:
            qs = qs.filter(organisation=organisation)
        configuration = qs.first()
        if configuration is None:
            configuration = ConfigurationOrganisation.objects.create(
                organisation=organisation
            )
        return configuration

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        context["identity_fields"] = [
            form["nom"],
            form["logo"],
            form["adresse"],
            form["telephone"],
            form["email"],
            form["site_web"],
            form["numero_fiscal"],
            form["devise"],
        ]
        context["document_fields"] = [
            form["prefixe_recu"],
            form["prefixe_attestation"],
            form["signature_nom"],
            form["signature_fonction"],
            form["signature_image"],
            form["cachet_image"],
        ]
        context["theme_fields"] = [
            form["couleur_sidebar"],
            form["couleur_header"],
            form["couleur_primaire"],
            form["couleur_secondaire"],
            form["couleur_accent"],
            form["couleur_fond"],
            form["couleur_surface"],
        ]
        context["theme_palettes"] = [
            {
                "code": "BALYS",
                "label": "BALY'S",
                "sidebar": "#0b2448",
                "header": "#ffffff",
                "primary": "#15519a",
                "secondary": "#102f5d",
                "accent": "#f28b16",
                "background": "#f4f6f9",
                "surface": "#ffffff",
            },
            {
                "code": "OCEAN",
                "label": "Ocean",
                "sidebar": "#083344",
                "header": "#f8fafc",
                "primary": "#0e7490",
                "secondary": "#155e75",
                "accent": "#f59e0b",
                "background": "#f1f5f9",
                "surface": "#ffffff",
            },
            {
                "code": "EMERALD",
                "label": "Emerald",
                "sidebar": "#064e3b",
                "header": "#ffffff",
                "primary": "#047857",
                "secondary": "#065f46",
                "accent": "#d97706",
                "background": "#f6f8f7",
                "surface": "#ffffff",
            },
            {
                "code": "BORDEAUX",
                "label": "Bordeaux",
                "sidebar": "#3f1222",
                "header": "#fffafa",
                "primary": "#8a1538",
                "secondary": "#5f1028",
                "accent": "#c98a2e",
                "background": "#f7f5f5",
                "surface": "#ffffff",
            },
        ]
        return context
