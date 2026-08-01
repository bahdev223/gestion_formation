from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.features import module_est_actif
from core.mixins import OrganisationScopedMixin
from organisations.access import effective_permissions, require_member_permission
from organisations.utils import require_request_organisation, tenant_reverse

from .catalogue import definitions_par_classe, obtenir
from .forms import OperationForm
from .models import Operation
from .services import OperationEngine


class TenantOperationPermissionMixin:
    """Autorise selon le role du membre dans l'entreprise courante."""

    tenant_permission_required = "finance.view"

    def dispatch(self, request, *args, **kwargs):
        require_member_permission(request, self.tenant_permission_required)
        return super().dispatch(request, *args, **kwargs)


class OperationIndexView(
    OrganisationScopedMixin, LoginRequiredMixin, TenantOperationPermissionMixin, ListView
):
    model = Operation
    template_name = "operations/index.html"
    context_object_name = "operations"
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
        flux = self.request.GET.get("flux")
        if flux in {"ENTREE", "SORTIE", "NEUTRE"}:
            codes = [
                definition.code
                for definition in _toutes_les_definitions()
                if definition.sens == flux
            ]
            queryset = queryset.filter(type_operation__in=codes)
        return queryset

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        organisation = self.get_current_organisation()
        toutes = Operation.objects.filter(organisation=organisation)
        validees = toutes.filter(statut=Operation.Statut.VALIDEE)
        codes_entree = [d.code for d in _toutes_les_definitions() if d.sens == "ENTREE"]
        codes_sortie = [d.code for d in _toutes_les_definitions() if d.sens == "SORTIE"]
        codes_neutre = [d.code for d in _toutes_les_definitions() if d.sens == "NEUTRE"]
        entrees = validees.filter(type_operation__in=codes_entree)
        sorties = validees.filter(type_operation__in=codes_sortie)
        transferts = validees.filter(type_operation__in=codes_neutre)
        contexte.update(
            {
                "groupes": definitions_par_classe(),
                "statut_actif": self.request.GET.get("statut", ""),
                "classe_active": self.request.GET.get("classe", ""),
                "flux_actif": self.request.GET.get("flux", ""),
                "compteurs": {
                    "total": toutes.count(),
                    "brouillon": toutes.filter(
                        statut=Operation.Statut.BROUILLON
                    ).count(),
                    "validee": toutes.filter(statut=Operation.Statut.VALIDEE).count(),
                    "annulee": toutes.filter(statut=Operation.Statut.ANNULEE).count(),
                    "entrees": entrees.count(),
                    "sorties": sorties.count(),
                    "transferts": transferts.count(),
                    "montant_entrees": entrees.aggregate(total=Sum("montant"))["total"] or 0,
                    "montant_sorties": sorties.aggregate(total=Sum("montant"))["total"] or 0,
                },
                "peut_gerer_operations": (
                    self.request.user.is_superuser
                    or "operations.manage"
                    in effective_permissions(
                        getattr(self.request, "organisation_member", None)
                    )
                ),
            }
        )
        return contexte


def _toutes_les_definitions():
    from .catalogue import CATALOGUE

    return CATALOGUE.values()


def _comptabilite_visible(organisation):
    return module_est_actif(organisation, "comptabilite")


class OperationCreateView(
    OrganisationScopedMixin, LoginRequiredMixin, TenantOperationPermissionMixin, CreateView
):
    model = Operation
    form_class = OperationForm
    template_name = "operations/form.html"
    tenant_permission_required = "operations.manage"

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
        operation.devise = organisation.devise
        operation.numero = OperationEngine.numeroter(
            organisation, operation.date_operation
        )
        operation.donnees = form.save(commit=False).donnees
        operation.save()
        self.object = operation

        # Le brouillon est enregistre meme si la comptabilisation echoue :
        # l'utilisateur ne doit pas perdre sa saisie.
        # Une operation saisie est finalisee par defaut. Le brouillon doit etre
        # un choix explicite afin d'eviter une liste d'operations inachevees.
        if self.request.POST.get("brouillon") != "1":
            try:
                OperationEngine.executer(operation, user=self.request.user)
            except ValidationError as erreur:
                messages.warning(
                    self.request,
                    (
                        "Opération enregistrée en brouillon : "
                        if _comptabilite_visible(organisation)
                        else "Opération non finalisée : "
                    )
                    + " ".join(erreur.messages),
                )
            else:
                messages.success(
                    self.request,
                    (
                        f"Opération {operation.numero} validée et comptabilisée."
                        if _comptabilite_visible(organisation)
                        else f"Opération {operation.numero} enregistrée et solde mis à jour."
                    ),
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
    OrganisationScopedMixin, LoginRequiredMixin, TenantOperationPermissionMixin, UpdateView
):
    model = Operation
    form_class = OperationForm
    template_name = "operations/form.html"
    tenant_permission_required = "operations.manage"

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
        if self.request.POST.get("brouillon") != "1":
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
    OrganisationScopedMixin, LoginRequiredMixin, TenantOperationPermissionMixin, DetailView
):
    model = Operation
    template_name = "operations/detail.html"
    context_object_name = "operation"

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


@require_POST
def valider_operation(request, organisation_slug, pk):
    """Comptabilise un brouillon."""
    organisation = require_request_organisation(request)
    require_member_permission(request, "operations.manage")

    operation = get_object_or_404(Operation, pk=pk, organisation=organisation)
    try:
        OperationEngine.executer(operation, user=request.user)
    except ValidationError as erreur:
        messages.error(request, " ".join(erreur.messages))
    else:
        messages.success(
            request, f"Opération {operation.numero} validée et comptabilisée."
        )
    destination = "operations:index" if request.POST.get("retour_liste") else "operations:detail"
    kwargs = {} if destination == "operations:index" else {"pk": operation.pk}
    return redirect(tenant_reverse(request, destination, kwargs=kwargs))


@require_POST
def annuler_operation(request, organisation_slug, pk):
    """Annule une operation. L'ecriture generee n'est pas supprimee."""
    organisation = require_request_organisation(request)
    require_member_permission(request, "operations.manage")

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
