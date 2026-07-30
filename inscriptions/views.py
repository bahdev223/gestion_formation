from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.shortcuts import redirect
from django.views.generic import CreateView, FormView, ListView

from core.mixins import HtmxModalFormMixin, OrganisationScopedMixin
from organisations.utils import tenant_reverse
from participants.models import Participant

from .forms import InscriptionForm, NouvelApprenantInscriptionForm
from .models import Inscription


class InscriptionIndexView(OrganisationScopedMixin, LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "inscriptions.view_inscription"
    model = Inscription
    template_name = "inscriptions/index.html"
    context_object_name = "inscriptions"
    paginate_by = 20

    def get_queryset(self):
        return super().get_queryset().select_related(
            "participant", "session", "session__formation"
        ).order_by("-date_inscription", "-created_at")


class InscriptionCreateView(OrganisationScopedMixin, HtmxModalFormMixin, LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "inscriptions.add_inscription"
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
        return tenant_reverse(
            self.request,
            "formations:session-detail",
            kwargs={"pk": self.object.session_id},
        )


class NouvelApprenantInscriptionView(HtmxModalFormMixin, LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = (
        "participants.add_participant",
        "inscriptions.add_inscription",
    )
    form_class = NouvelApprenantInscriptionForm
    template_name = "inscriptions/new_learner_form.html"
    modal_title = "Nouvel apprenant et inscription"
    modal_eyebrow = "Inscriptions"
    submit_label = "Créer et inscrire"
    full_width_fields = "session observations"

    def get_current_organisation(self):
        organisation = getattr(self.request, "organisation", None)
        if organisation is not None:
            return organisation
        from organisations.models import Organisation

        return Organisation.objects.filter(slug="balys-group").first()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        organisation = self.get_current_organisation()
        if organisation is not None:
            kwargs["organisation"] = organisation
        return kwargs

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
        organisation = self.get_current_organisation()
        participant = Participant.objects.create(
            organisation=organisation,
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
            organisation=organisation,
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
        target_url = tenant_reverse(
            self.request,
            "formations:session-detail",
            kwargs={"pk": inscription.session_id},
        )
        response = redirect(target_url)
        if self.is_htmx():
            response.status_code = 204
            response["HX-Redirect"] = tenant_reverse(
                self.request,
                "formations:session-detail",
                kwargs={"pk": inscription.session_id},
            )
        return response
