from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import models
from django.views.generic import CreateView, ListView

from core.mixins import HtmxModalFormMixin, OrganisationScopedMixin
from organisations.utils import tenant_reverse

from .forms import ParticipantForm
from .models import Participant


class ParticipantIndexView(OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "participants.view_participant"
    model = Participant
    template_name = "participants/index.html"
    context_object_name = "participants"
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            inscriptions_count=models.Count("inscriptions", distinct=True),
            total_paye_sum=models.Sum(
                "inscriptions__paiements__montant",
                filter=models.Q(inscriptions__paiements__statut="VALIDE"),
            ),
        )
        search = self.request.GET.get("q", "").strip()
        statut = self.request.GET.get("statut", "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(matricule__icontains=search)
                | models.Q(nom__icontains=search)
                | models.Q(prenom__icontains=search)
                | models.Q(telephone__icontains=search)
                | models.Q(email__icontains=search)
                | models.Q(profession__icontains=search)
                | models.Q(entreprise__icontains=search)
            )
        if statut:
            queryset = queryset.filter(statut=statut)
        return queryset.order_by("nom", "prenom")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = self.get_queryset()
        context.update(
            {
                "search_query": self.request.GET.get("q", "").strip(),
                "active_statut": self.request.GET.get("statut", "").strip(),
                "statut_choices": Participant.Statut.choices,
                "participants_total": base_qs.count(),
                "participants_actifs": base_qs.filter(
                    statut=Participant.Statut.ACTIF,
                ).count(),
                "participants_entreprises": base_qs.exclude(
                    entreprise="",
                ).count(),
                "participants_inscriptions": sum(
                    participant.inscriptions_count for participant in base_qs
                ),
            }
        )
        return context


class ParticipantCreateView(OrganisationScopedMixin, HtmxModalFormMixin, LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "participants.add_participant"
    model = Participant
    form_class = ParticipantForm
    template_name = "participants/form.html"
    success_message = "La fiche du participant a été créée."
    modal_title = "Nouveau participant"
    modal_eyebrow = "Apprenants"
    submit_label = "Enregistrer le participant"
    full_width_fields = "adresse notes photo"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["session_id"] = self.request.GET.get("session", "")
        return context

    def get_success_url(self):
        session_id = self.request.POST.get("session_id")
        if session_id:
            return (
                tenant_reverse(self.request, "inscriptions:create")
                + f"?session={session_id}&participant={self.object.pk}"
            )
        return tenant_reverse(self.request, "participants:index")
