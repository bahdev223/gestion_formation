from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import DetailView, ListView

from organisations.utils import require_request_organisation

from ..models import JournalComptable
from ..services.journal_service import BalanceService, GrandLivreService
from .views_bilan import ScopedExerciceMixin


class JournalListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = JournalComptable
    template_name = "comptabilite_ohada/journal_list.html"
    context_object_name = "journaux"
    permission_required = "comptabilite_ohada.view_journalcomptable"


class JournalDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = JournalComptable
    template_name = "comptabilite_ohada/journal_detail.html"
    context_object_name = "journal"
    permission_required = "comptabilite_ohada.view_journalcomptable"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Les ecritures du journal doivent rester limitees au tenant courant :
        # un JournalComptable est partage entre les organisations.
        context["ecritures"] = (
            self.object.ecritures.filter(
                organisation=require_request_organisation(self.request)
            )
            .select_related("exercice")
            .order_by("-date_ecriture")[:50]
        )
        return context


class BalanceView(
    ScopedExerciceMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView
):
    template_name = "comptabilite_ohada/balance.html"
    permission_required = "comptabilite_ohada.view_ecriturecomptable"

    def get_queryset(self):
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organisation = self.get_organisation()
        context["balance"] = BalanceService().balance(
            organisation=organisation,
            exercice=self.get_scoped_exercice(organisation),
        )
        context["total_debit"] = sum(l["total_debit"] for l in context["balance"])
        context["total_credit"] = sum(l["total_credit"] for l in context["balance"])
        return context


class GrandLivreView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    template_name = "comptabilite_ohada/grand_livre.html"
    permission_required = "comptabilite_ohada.view_ecriturecomptable"

    def get_queryset(self):
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organisation = self.get_organisation()
        context["lignes"] = GrandLivreService().grand_livre(
            organisation=organisation,
            compte_code=self.request.GET.get("compte"),
            exercice=self.get_scoped_exercice(organisation),
        )
        return context
