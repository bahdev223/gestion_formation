from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import redirect
from django.views.generic import CreateView, DetailView, ListView

from organisations.utils import require_request_organisation, tenant_reverse

from ..models import ExerciceComptable
from ..services.exercice_service import ExerciceService


class OrganisationFilteredQuerysetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(organisation=require_request_organisation(self.request))
        return qs


class ExerciceListView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    OrganisationFilteredQuerysetMixin,
    ListView,
):
    model = ExerciceComptable
    template_name = "comptabilite_ohada/exercice_list.html"
    context_object_name = "exercices"
    permission_required = "comptabilite_ohada.view_exercicecomptable"


class ExerciceDetailView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    OrganisationFilteredQuerysetMixin,
    DetailView,
):
    model = ExerciceComptable
    template_name = "comptabilite_ohada/exercice_detail.html"
    context_object_name = "exercice"
    permission_required = "comptabilite_ohada.view_exercicecomptable"


class ExerciceCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = ExerciceComptable
    template_name = "comptabilite_ohada/exercice_form.html"
    fields = ["code", "date_debut", "date_fin"]
    permission_required = "comptabilite_ohada.add_exercicecomptable"

    def get_success_url(self):
        return tenant_reverse(
            self.request,
            "comptabilite:exercice_detail",
            kwargs={"pk": self.object.pk},
        )

    def form_valid(self, form):
        form.instance.organisation = require_request_organisation(self.request)
        messages.success(self.request, "Exercice créé avec succès.")
        return super().form_valid(form)


class ExerciceCloturerView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    OrganisationFilteredQuerysetMixin,
    DetailView,
):
    model = ExerciceComptable
    permission_required = "comptabilite_ohada.change_exercicecomptable"

    def post(self, request, *args, **kwargs):
        exercice = self.get_object()
        try:
            ExerciceService.cloturer(exercice, request.user)
            messages.success(request, "Exercice clôturé avec succès.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect(
            tenant_reverse(
                request,
                "comptabilite:exercice_detail",
                kwargs={"pk": exercice.pk},
            )
        )


class ExerciceRouvrirView(
    LoginRequiredMixin,
    PermissionRequiredMixin,
    OrganisationFilteredQuerysetMixin,
    DetailView,
):
    model = ExerciceComptable
    permission_required = "comptabilite_ohada.change_exercicecomptable"

    def post(self, request, *args, **kwargs):
        exercice = self.get_object()
        try:
            ExerciceService.rouvrir(exercice)
            messages.success(request, "Exercice rouvert avec succès.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect(
            tenant_reverse(
                request,
                "comptabilite:exercice_detail",
                kwargs={"pk": exercice.pk},
            )
        )
