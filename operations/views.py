from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import OrganisationScopedMixin
from organisations.utils import require_request_organisation, tenant_reverse

from .catalogue import definitions_par_classe, obtenir
from .forms import OperationForm
from .models import Operation
from .services import OperationEngine


class OperationIndexView(
    OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView
):
    model = Operation
    template_name = "operations/index.html"
    context_object_name = "operations"
    permission_required = "operations.view_operation"
    paginate_by = 25

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("compte_tresorerie", "ecriture", "cree_par")
        )
        statut = self.request.GET.get("statut")
        if statut in dict(Operation.Statut.choices):
            queryset = queryset.filter(statut=statut)
        classe = self.request.GET.get("classe")
        if classe:
            codes = [
                definition.code
                for definition in _toutes_les_definitions()
                if definition.classe == classe
            ]
            queryset = queryset.filter(type_operation__in=codes)
        return queryset

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        organisation = self.get_current_organisation()
        toutes = Operation.objects.filter(organisation=organisation)
        contexte.update(
            {
                "groupes": definitions_par_classe(),
                "statut_actif": self.request.GET.get("statut", ""),
                "classe_active": self.request.GET.get("classe", ""),
                "compteurs": {
                    "total": toutes.count(),
                    "brouillon": toutes.filter(
                        statut=Operation.Statut.BROUILLON
                    ).count(),
                    "validee": toutes.filter(statut=Operation.Statut.VALIDEE).count(),
                    "annulee": toutes.filter(statut=Operation.Statut.ANNULEE).count(),
                },
            }
        )
        return contexte


def _toutes_les_definitions():
    from .catalogue import CATALOGUE

    return CATALOGUE.values()


class OperationCreateView(
    OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, CreateView
):
    model = Operation
    form_class = OperationForm
    template_name = "operations/form.html"
    permission_required = "operations.add_operation"

    def get_initial(self):
        initial = super().get_initial()
        type_demande = self.request.GET.get("type")
        if type_demande and obtenir(type_demande):
            initial["type_operation"] = type_demande
        return initial

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["groupes"] = definitions_par_classe()
        contexte["definition"] = getattr(contexte["form"], "definition", None)
        return contexte

    def form_valid(self, form):
        organisation = self.get_current_organisation()
        operation = form.save(commit=False)
        operation.organisation = organisation
        operation.cree_par = self.request.user
        operation.numero = OperationEngine.numeroter(
            organisation, operation.date_operation
        )
        operation.donnees = form.save(commit=False).donnees
        operation.save()
        self.object = operation

        # Le brouillon est enregistre meme si la comptabilisation echoue :
        # l'utilisateur ne doit pas perdre sa saisie.
        if self.request.POST.get("valider") == "1":
            try:
                OperationEngine.executer(operation, user=self.request.user)
            except ValidationError as erreur:
                messages.warning(
                    self.request,
                    "Opération enregistrée en brouillon : "
                    + " ".join(erreur.messages),
                )
            else:
                messages.success(
                    self.request,
                    f"Opération {operation.numero} validée et comptabilisée.",
                )
        else:
            messages.success(
                self.request, f"Opération {operation.numero} enregistrée en brouillon."
            )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return tenant_reverse(
            self.request, "operations:detail", kwargs={"pk": self.object.pk}
        )


class OperationUpdateView(
    OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, UpdateView
):
    model = Operation
    form_class = OperationForm
    template_name = "operations/form.html"
    permission_required = "operations.change_operation"

    def get_queryset(self):
        # Une operation validee est comptabilisee : elle n'est plus modifiable.
        return super().get_queryset().filter(statut=Operation.Statut.BROUILLON)

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["groupes"] = definitions_par_classe()
        contexte["definition"] = getattr(contexte["form"], "definition", None)
        return contexte

    def form_valid(self, form):
        operation = form.save()
        self.object = operation
        if self.request.POST.get("valider") == "1":
            try:
                OperationEngine.executer(operation, user=self.request.user)
            except ValidationError as erreur:
                messages.warning(self.request, " ".join(erreur.messages))
            else:
                messages.success(
                    self.request, f"Opération {operation.numero} comptabilisée."
                )
        else:
            messages.success(self.request, "Brouillon mis à jour.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return tenant_reverse(
            self.request, "operations:detail", kwargs={"pk": self.object.pk}
        )


class OperationDetailView(
    OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView
):
    model = Operation
    template_name = "operations/detail.html"
    context_object_name = "operation"
    permission_required = "operations.view_operation"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "compte_tresorerie",
                "compte_destination",
                "ecriture",
                "ecriture__journal",
                "cree_par",
                "validee_par",
            )
        )

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        operation = self.object
        contexte["lignes_ecriture"] = (
            operation.ecriture.lignes.select_related("compte")
            if operation.ecriture_id
            else []
        )
        return contexte


def valider_operation(request, organisation_slug, pk):
    """Comptabilise un brouillon."""
    organisation = require_request_organisation(request)
    if not request.user.has_perm("operations.change_operation"):
        messages.error(request, "Vous n'avez pas le droit de valider une opération.")
        return redirect(tenant_reverse(request, "operations:index"))

    operation = get_object_or_404(Operation, pk=pk, organisation=organisation)
    try:
        OperationEngine.executer(operation, user=request.user)
    except ValidationError as erreur:
        messages.error(request, " ".join(erreur.messages))
    else:
        messages.success(
            request, f"Opération {operation.numero} validée et comptabilisée."
        )
    return redirect(
        tenant_reverse(request, "operations:detail", kwargs={"pk": operation.pk})
    )


def annuler_operation(request, organisation_slug, pk):
    """Annule une operation. L'ecriture generee n'est pas supprimee."""
    organisation = require_request_organisation(request)
    if not request.user.has_perm("operations.change_operation"):
        messages.error(request, "Vous n'avez pas le droit d'annuler une opération.")
        return redirect(tenant_reverse(request, "operations:index"))

    operation = get_object_or_404(Operation, pk=pk, organisation=organisation)
    if operation.statut == Operation.Statut.VALIDEE:
        messages.error(
            request,
            "Une opération comptabilisée ne peut pas être annulée ici : "
            "passez par une écriture d'annulation en comptabilité.",
        )
    else:
        operation.statut = Operation.Statut.ANNULEE
        operation.motif_annulation = request.POST.get("motif", "")
        operation.save(update_fields=["statut", "motif_annulation", "updated_at"])
        messages.success(request, f"Opération {operation.numero} annulée.")
    return redirect(
        tenant_reverse(request, "operations:detail", kwargs={"pk": operation.pk})
    )
