from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView

from core.mixins import HtmxModalFormMixin, OrganisationScopedMixin
from inscriptions.services.inscription_service import recalculate_payment_status

from .forms import PaiementForm
from .models import Paiement
from .services.mouvement_sync_service import ensure_payment_movement


class PaiementIndexView(OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "paiements.view_paiement"
    model = Paiement
    template_name = "paiements/index.html"
    context_object_name = "paiements"
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "inscription",
            "inscription__participant",
            "inscription__session",
            "inscription__session__formation",
            "enregistre_par",
            "compte",
        )
        utilisateur_id = self.request.GET.get("utilisateur")
        compte_id = self.request.GET.get("compte")
        statut = self.request.GET.get("statut")
        date_debut = self.request.GET.get("date_debut")
        date_fin = self.request.GET.get("date_fin")
        if utilisateur_id:
            queryset = queryset.filter(enregistre_par_id=utilisateur_id)
        if compte_id:
            queryset = queryset.filter(compte_id=compte_id)
        if statut:
            queryset = queryset.filter(statut=statut)
        if date_debut:
            queryset = queryset.filter(date_paiement__date__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(date_paiement__date__lte=date_fin)
        return queryset.order_by("-date_paiement", "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["payment_currency"] = self.get_current_organisation().devise
        organisation = self.get_current_organisation()
        context["payment_users"] = organisation.membres.filter(
            is_active=True
        ).select_related("user")
        from comptes.models import Compte
        context["payment_accounts"] = Compte.objects.filter(
            organisation=organisation, actif=True
        ).order_by("nom")
        context["payment_statuses"] = Paiement.Statut.choices
        context["filters"] = self.request.GET
        valid_payments = self.get_queryset().filter(statut=Paiement.Statut.VALIDE)
        context["total_encaisse"] = (
            valid_payments.aggregate(total=Sum("montant"))["total"] or 0
        )
        context["encaisse_jour"] = (
            valid_payments.filter(
                date_paiement__date=timezone.localdate()
            ).aggregate(total=Sum("montant"))["total"]
            or 0
        )
        context["paiements_valides"] = valid_payments.count()
        context["paiements_annules"] = self.get_queryset().filter(
            statut=Paiement.Statut.ANNULE
        ).count()
        return context


class PaiementCreateView(OrganisationScopedMixin, HtmxModalFormMixin, LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "paiements.add_paiement"
    model = Paiement
    form_class = PaiementForm
    template_name = "paiements/form.html"
    tenant_success_view_name = "paiements:index"
    success_message = "Le paiement a été enregistré et le reçu a été créé."
    modal_title = "Nouveau paiement"
    modal_eyebrow = "Encaissements formations"
    submit_label = "Valider et créer le reçu"
    full_width_fields = "inscription observations"

    def get_template_names(self):
        if self.is_htmx():
            return ["paiements/modal_form.html"]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["payment_currency"] = self.get_current_organisation().devise
        form = context["form"]
        context["account_mode_map"] = {
            str(compte.pk): PaiementForm.ACCOUNT_TYPE_TO_MODE.get(compte.type, "")
            for compte in form.fields["compte"].queryset
        }
        inscriptions = form.fields["inscription"].queryset.annotate(
            total_paye_calc=Coalesce(
                Sum(
                    "paiements__montant",
                    filter=Q(paiements__statut=Paiement.Statut.VALIDE),
                ),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        context["inscription_summaries"] = {
            str(inscription.pk): {
                "participant": inscription.participant.nom_complet,
                "formation": inscription.session.formation.nom,
                "session": inscription.session.titre,
                "montant": float(inscription.montant_final),
                "paye": float(inscription.total_paye_calc or 0),
                "reste": float(
                    max(
                        inscription.montant_final - (inscription.total_paye_calc or 0),
                        0,
                    )
                ),
            }
            for inscription in inscriptions
        }
        return context

    @transaction.atomic
    def form_valid(self, form):
        form.instance.enregistre_par = self.request.user
        response = super().form_valid(form)
        ensure_payment_movement(self.object, user=self.request.user)
        recalculate_payment_status(self.object.inscription)
        return response


class PaiementDetailView(OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    permission_required = "paiements.view_paiement"
    model = Paiement
    template_name = "paiements/detail.html"
    context_object_name = "paiement"

    def get_queryset(self):
        return super().get_queryset().select_related(
            "inscription",
            "inscription__participant",
            "inscription__session",
            "inscription__session__formation",
            "enregistre_par",
            "compte",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["payment_currency"] = self.get_current_organisation().devise
        return context
