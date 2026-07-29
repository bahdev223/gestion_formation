from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from decimal import Decimal

from django.db.models import Count, Sum
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import UpdateView

from formations.models import Formation, SessionFormation
from inscriptions.models import Inscription
from paiements.models import Paiement
from participants.models import Participant

from .forms import ConfigurationOrganisationForm
from .models import ConfigurationOrganisation


@login_required
def dashboard_home(request):
    today = timezone.localdate()
    valid_payments = Paiement.objects.filter(statut=Paiement.Statut.VALIDE)
    active_registrations = Inscription.objects.exclude(
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
        SessionFormation.objects.filter(date_fin__gte=today)
        .exclude(statut=SessionFormation.Statut.ANNULEE)
        .select_related("formation", "formateur")
        .annotate(inscrits_count=Count("inscriptions"))
        .order_by("date_debut")[:5]
    )
    context = {
        "title": "Tableau de bord",
        "formations_actives": Formation.objects.filter(
            statut=Formation.Statut.ACTIVE
        ).count(),
        "participants_count": Participant.objects.count(),
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
    success_url = reverse_lazy("dashboard:organisation-settings")
    success_message = "Les paramètres de l’entreprise ont été enregistrés."

    def get_object(self, queryset=None):
        configuration = ConfigurationOrganisation.objects.order_by("pk").first()
        if configuration is None:
            configuration = ConfigurationOrganisation.objects.create()
        return configuration
