from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView

from inscriptions.services.inscription_service import recalculate_payment_status
from core.mixins import HtmxModalFormMixin

from .forms import PaiementForm
from .models import Paiement


class PaiementIndexView(LoginRequiredMixin, ListView):
    model = Paiement
    template_name = "paiements/index.html"
    context_object_name = "paiements"
    paginate_by = 25

    def get_queryset(self):
        return Paiement.objects.select_related(
            "inscription",
            "inscription__participant",
            "inscription__session",
            "inscription__session__formation",
            "enregistre_par",
        ).order_by("-date_paiement", "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        valid_payments = Paiement.objects.filter(statut=Paiement.Statut.VALIDE)
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
        context["paiements_annules"] = Paiement.objects.filter(
            statut=Paiement.Statut.ANNULE
        ).count()
        return context


class PaiementCreateView(HtmxModalFormMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Paiement
    form_class = PaiementForm
    template_name = "paiements/form.html"
    success_url = reverse_lazy("paiements:index")
    success_message = "Le paiement a été enregistré et le reçu a été créé."
    modal_title = "Nouveau paiement"
    modal_eyebrow = "Encaissements formations"
    submit_label = "Valider et créer le reçu"
    full_width_fields = "inscription observations"

    def form_valid(self, form):
        form.instance.enregistre_par = self.request.user
        response = super().form_valid(form)
        recalculate_payment_status(self.object.inscription)
        return response


class PaiementDetailView(LoginRequiredMixin, DetailView):
    model = Paiement
    template_name = "paiements/detail.html"
    context_object_name = "paiement"

    def get_queryset(self):
        return Paiement.objects.select_related(
            "inscription",
            "inscription__participant",
            "inscription__session",
            "inscription__session__formation",
            "enregistre_par",
        )
