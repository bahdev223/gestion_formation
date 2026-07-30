from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import DetailView, ListView

from organisations.utils import get_request_organisation

from ..models import Immobilisation


class OrganisationFilteredQuerysetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        organisation = get_request_organisation(self.request)
        if organisation is not None:
            qs = qs.filter(organisation=organisation)
        return qs


class ImmobilisationListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    OrganisationFilteredQuerysetMixin,
    ListView,
):
    model = Immobilisation
    template_name = "comptabilite_ohada/immobilisation_list.html"
    context_object_name = "immobilisations"
    permission_required = "comptabilite_ohada.view_immobilisation"


class ImmobilisationDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    OrganisationFilteredQuerysetMixin,
    DetailView,
):
    model = Immobilisation
    template_name = "comptabilite_ohada/immobilisation_detail.html"
    context_object_name = "immobilisation"
    permission_required = "comptabilite_ohada.view_immobilisation"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plan"] = self.object.plan_amortissement.all()
        return context
