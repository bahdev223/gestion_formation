from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
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
        return super().get_queryset().order_by("nom", "prenom")


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
