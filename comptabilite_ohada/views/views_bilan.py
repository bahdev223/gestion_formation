from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from organisations.utils import require_request_organisation

from ..models import ExerciceComptable
from ..services.bilan_service import BilanService


class ScopedExerciceMixin:
    """Resout l'exercice de la query string dans l'organisation courante."""

    def get_organisation(self):
        return require_request_organisation(self.request)

    def get_scoped_exercice(self, organisation):
        exercice_id = self.request.GET.get("exercice")
        if not exercice_id:
            return None
        # Filtre par organisation : sinon un exercice d'un autre client
        # pouvait etre passe aux etats financiers.
        return get_object_or_404(
            ExerciceComptable, pk=exercice_id, organisation=organisation
        )


class BilanView(
    ScopedExerciceMixin, LoginRequiredMixin, PermissionRequiredMixin, TemplateView
):
    template_name = "comptabilite_ohada/bilan.html"
    permission_required = "comptabilite_ohada.view_ecriturecomptable"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organisation = self.get_organisation()
        exercice = self.get_scoped_exercice(organisation)
        service = BilanService()
        context["bilan"] = service.bilan(
            organisation=organisation, exercice=exercice
        )
        context["resultat"] = service.compte_resultat(
            organisation=organisation, exercice=exercice
        )
        return context


class CompteResultatView(
    ScopedExerciceMixin, LoginRequiredMixin, PermissionRequiredMixin, TemplateView
):
    template_name = "comptabilite_ohada/compte_resultat.html"
    permission_required = "comptabilite_ohada.view_ecriturecomptable"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organisation = self.get_organisation()
        context["resultat"] = BilanService().compte_resultat(
            organisation=organisation,
            exercice=self.get_scoped_exercice(organisation),
        )
        return context
