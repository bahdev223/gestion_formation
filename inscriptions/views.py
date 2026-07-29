from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, FormView, ListView

from participants.models import Participant
from core.mixins import HtmxModalFormMixin

from .forms import InscriptionForm, NouvelApprenantInscriptionForm
from .models import Inscription


class InscriptionIndexView(LoginRequiredMixin, ListView):
    model = Inscription
    template_name = "inscriptions/index.html"
    context_object_name = "inscriptions"
    paginate_by = 20

    def get_queryset(self):
        return Inscription.objects.select_related(
            "participant", "session", "session__formation"
        ).order_by("-date_inscription", "-created_at")


class InscriptionCreateView(HtmxModalFormMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Inscription
    form_class = InscriptionForm
    template_name = "inscriptions/form.html"
    success_message = "L’inscription a été enregistrée avec succès."
    modal_title = "Nouvelle inscription"
    modal_eyebrow = "Inscriptions"
    submit_label = "Valider l’inscription"
    full_width_fields = "participant session observations"

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("session"):
            initial["session"] = self.request.GET["session"]
        if self.request.GET.get("participant"):
            initial["participant"] = self.request.GET["participant"]
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["session_id"] = self.request.GET.get("session", "")
        return context

    def form_valid(self, form):
        form.instance.cree_par = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "formations:session-detail",
            kwargs={"pk": self.object.session_id},
        )


class NouvelApprenantInscriptionView(HtmxModalFormMixin, LoginRequiredMixin, FormView):
    form_class = NouvelApprenantInscriptionForm
    template_name = "inscriptions/new_learner_form.html"
    modal_title = "Nouvel apprenant et inscription"
    modal_eyebrow = "Inscriptions"
    submit_label = "Créer et inscrire"
    full_width_fields = "session observations"

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("date"):
            initial["date_inscription"] = self.request.GET["date"]
        if self.request.GET.get("session"):
            initial["session"] = self.request.GET["session"]
        return initial

    @transaction.atomic
    def form_valid(self, form):
        data = form.cleaned_data
        participant = Participant.objects.create(
            prenom=data["prenom"],
            nom=data["nom"],
            telephone=data["telephone"],
            email=data["email"],
            genre=data["genre"],
            date_naissance=data["date_naissance"],
            ville=data["ville"],
            profession=data["profession"],
            entreprise=data["entreprise"],
        )
        session = data["session"]
        inscription = Inscription.objects.create(
            participant=participant,
            session=session,
            date_inscription=data["date_inscription"],
            prix_initial=session.prix_applique,
            remise=data["remise"],
            montant_final=session.prix_applique - data["remise"],
            statut=data["statut"],
            observations=data["observations"],
            cree_par=self.request.user,
        )
        messages.success(
            self.request,
            f"{participant.nom_complet} a été créé et inscrit à la session.",
        )
        response = redirect(
            "formations:session-detail",
            pk=inscription.session_id,
        )
        if self.is_htmx():
            response.status_code = 204
            response["HX-Redirect"] = reverse(
                "formations:session-detail",
                kwargs={"pk": inscription.session_id},
            )
        return response
