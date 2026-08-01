from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DeleteView, DetailView, ListView, View

from organisations.utils import require_request_organisation, tenant_reverse

from ..forms import EcritureForm, LigneEcritureFormSet
from ..models import CompteComptable, EcritureComptable
from ..services.ecriture_service import EcritureService
from ..services.initialisation_service import InitialisationService


class EcritureListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = EcritureComptable
    template_name = "comptabilite_ohada/ecriture_list.html"
    context_object_name = "ecritures"
    permission_required = "comptabilite_ohada.view_ecriturecomptable"
    paginate_by = 25

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("journal", "exercice")
            .prefetch_related("lignes__compte")
        )
        qs = qs.filter(organisation=require_request_organisation(self.request))
        status = self.request.GET.get("status")
        if status == "validee":
            qs = qs.filter(validee=True)
        elif status == "non_validee":
            qs = qs.filter(validee=False)
        return qs.order_by("-date_ecriture", "-created_at")


class EcritureDetailView(
    LoginRequiredMixin, PermissionRequiredMixin, DetailView
):
    model = EcritureComptable
    template_name = "comptabilite_ohada/ecriture_detail.html"
    context_object_name = "ecriture"
    permission_required = "comptabilite_ohada.view_ecriturecomptable"

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("journal", "exercice")
            .prefetch_related("lignes__compte")
        )
        qs = qs.filter(organisation=require_request_organisation(self.request))
        return qs


class EcritureFormView(LoginRequiredMixin, PermissionRequiredMixin, View):
    template_name = "comptabilite_ohada/ecriture_form.html"
    permission_required = "comptabilite_ohada.add_ecriturecomptable"
    object = None

    def get_object(self):
        return None

    def get_organisation(self):
        organisation = require_request_organisation(self.request)
        InitialisationService.initialiser_organisation(organisation)
        return organisation

    def build_formset(self, *args, **kwargs):
        formset = LigneEcritureFormSet(*args, **kwargs)
        comptes = CompteComptable.objects.filter(
            organisation=self.get_organisation(), actif=True
        ).order_by("code")
        for ligne_form in formset.forms:
            ligne_form.fields["compte"].queryset = comptes
        return formset

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render_forms(
            EcritureForm(instance=self.object, organisation=self.get_organisation()),
            self.build_formset(instance=self.object),
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = EcritureForm(
            request.POST, instance=self.object, organisation=self.get_organisation()
        )
        formset = self.build_formset(
            request.POST, instance=self.object
        )
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                ecriture = form.save(commit=False)
                ecriture.created_by = request.user.get_username()
                ecriture.validee = False
                ecriture.organisation = require_request_organisation(request)
                ecriture.save()
                formset.instance = ecriture
                formset.save()
            messages.success(
                request,
                "Écriture enregistrée en brouillon. Vérifiez-la avant validation.",
            )
            return redirect(
                tenant_reverse(
                    request,
                    "comptabilite:ecriture_detail",
                    kwargs={"pk": ecriture.pk},
                )
            )
        return self.render_forms(form, formset)

    def render_forms(self, form, formset):
        return render(
            self.request,
            self.template_name,
            {"form": form, "formset": formset, "object": self.object},
        )


class EcritureCreateView(EcritureFormView):
    pass


class EcritureUpdateView(EcritureFormView):
    permission_required = "comptabilite_ohada.change_ecriturecomptable"

    def get_object(self):
        return get_object_or_404(
            EcritureComptable,
            pk=self.kwargs["pk"],
            validee=False,
            organisation=require_request_organisation(self.request),
        )


class EcritureDeleteView(
    LoginRequiredMixin, PermissionRequiredMixin, DeleteView
):
    model = EcritureComptable
    template_name = "comptabilite_ohada/ecriture_confirm_delete.html"
    permission_required = "comptabilite_ohada.delete_ecriturecomptable"

    def get_success_url(self):
        return tenant_reverse(self.request, "comptabilite:ecriture_list")

    def get_queryset(self):
        qs = super().get_queryset().filter(validee=False)
        qs = qs.filter(organisation=require_request_organisation(self.request))
        return qs

    def form_valid(self, form):
        messages.success(self.request, "Écriture brouillon supprimée.")
        return super().form_valid(form)


class EcritureValiderView(
    LoginRequiredMixin, PermissionRequiredMixin, DetailView
):
    model = EcritureComptable
    permission_required = "comptabilite_ohada.change_ecriturecomptable"

    def post(self, request, *args, **kwargs):
        ecriture = get_object_or_404(
            EcritureComptable,
            pk=self.kwargs["pk"],
            organisation=require_request_organisation(request),
        )
        try:
            EcritureService.valider_ecriture(ecriture, request.user)
            messages.success(request, "Écriture validée avec succès.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect(
            tenant_reverse(
                request,
                "comptabilite:ecriture_detail",
                kwargs={"pk": ecriture.pk},
            )
        )
