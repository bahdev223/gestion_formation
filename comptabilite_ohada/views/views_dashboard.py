from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView

from organisations.utils import require_request_organisation

from ..services.dashboard_service import DashboardService
from ..services.initialisation_service import InitialisationService


class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "comptabilite_ohada/dashboard.html"
    permission_required = "comptabilite_ohada.view_ecriturecomptable"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organisation = require_request_organisation(self.request)
        InitialisationService.initialiser_organisation(organisation)
        service = DashboardService(organisation=organisation)
        context["total_ecritures"] = service.compter_ecritures()
        context["ecritures_non_validees"] = service.compter_ecritures_non_validees()
        context["dernieres_ecritures"] = service.dernieres_ecritures()
        context["exercice_courant"] = service.exercice_courant()
        context["totaux_par_journal"] = service.totaux_par_journal()
        context["synthese"] = service.synthese()
        context["alertes"] = service.alertes()
        evolution = service.evolution_tresorerie(30)
        context["graphique_tresorerie"] = {
            "labels": [item["date"].strftime("%d/%m") for item in evolution],
            "entrees": [float(item["debit"] or 0) for item in evolution],
            "sorties": [float(item["credit"] or 0) for item in evolution],
        }
        journaux = list(context["totaux_par_journal"])
        context["totaux_par_journal"] = journaux
        context["graphique_journaux"] = {
            "labels": [item["journal__code"] or "Sans journal" for item in journaux],
            "valeurs": [float(item["total"] or 0) for item in journaux],
        }
        context["devise"] = organisation.devise
        return context
