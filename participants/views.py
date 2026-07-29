from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.views.generic import CreateView, ListView

from core.mixins import HtmxModalFormMixin
from .forms import ParticipantForm
from .models import Participant


class ParticipantIndexView(LoginRequiredMixin, ListView):
    model = Participant
    template_name = "participants/index.html"
    context_object_name = "participants"
    paginate_by = 25

    def get_queryset(self):
        return Participant.objects.order_by("nom", "prenom")


class ParticipantCreateView(HtmxModalFormMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
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
                reverse("inscriptions:create")
                + f"?session={session_id}&participant={self.object.pk}"
            )
        return reverse("participants:index")
