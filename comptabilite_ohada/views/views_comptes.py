from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from organisations.utils import require_request_organisation

from ..forms import CompteComptableForm, RequestOrganisationFormMixin
from ..models import CompteComptable
from ..services.initialisation_service import InitialisationService


class CompteComptableListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = CompteComptable
    template_name = "comptabilite_ohada/compte_list.html"
    context_object_name = "comptes"
    permission_required = "comptabilite_ohada.view_comptecomptable"

    def get_queryset(self):
        organisation = require_request_organisation(self.request)
        InitialisationService.initialiser_organisation(organisation)
        qs = super().get_queryset().filter(organisation=organisation)
        classe = self.request.GET.get("classe")
        if classe and classe in "12345678":
            qs = qs.filter(code__startswith=classe)
        actif = self.request.GET.get("actif")
        if actif in {"0", "1"}:
            qs = qs.filter(actif=(actif == "1"))
        return qs.order_by("code")


class CompteComptableDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = CompteComptable
    template_name = "comptabilite_ohada/compte_detail.html"
    context_object_name = "compte"
    permission_required = "comptabilite_ohada.view_comptecomptable"

    def get_queryset(self):
        return super().get_queryset().filter(
            organisation=require_request_organisation(self.request)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["solde"] = self.object.calculer_solde()
        return context


class CompteComptableCreateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RequestOrganisationFormMixin,
    CreateView,
):
    model = CompteComptable
    form_class = CompteComptableForm
    template_name = "comptabilite_ohada/compte_form.html"
    permission_required = "comptabilite_ohada.add_comptecomptable"

    def form_valid(self, form):
        form.instance.organisation = require_request_organisation(self.request)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "organisations:comptabilite:compte_detail",
            kwargs={
                "organisation_slug": self.request.organisation.slug,
                "pk": self.object.pk,
            },
        )


class CompteComptableUpdateView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    RequestOrganisationFormMixin,
    UpdateView,
):
    model = CompteComptable
    form_class = CompteComptableForm
    template_name = "comptabilite_ohada/compte_form.html"
    permission_required = "comptabilite_ohada.change_comptecomptable"

    def get_queryset(self):
        return super().get_queryset().filter(
            organisation=require_request_organisation(self.request)
        )

    def get_success_url(self):
        return reverse(
            "organisations:comptabilite:compte_detail",
            kwargs={
                "organisation_slug": self.request.organisation.slug,
                "pk": self.object.pk,
            },
        )
