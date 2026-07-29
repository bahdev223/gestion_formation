from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from core.mixins import HtmxModalFormMixin
from .forms import (
    CategorieFormationForm,
    FormationForm,
    SeanceForm,
    SessionFormationForm,
)
from .models import CategorieFormation, Formation, Seance, SessionFormation


class FormationIndexView(LoginRequiredMixin, ListView):
    model = Formation
    template_name = "formations/index.html"
    context_object_name = "formations"
    paginate_by = 20

    def get_queryset(self):
        return Formation.objects.select_related("categorie").order_by("-created_at")


class FormationCreateView(HtmxModalFormMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Formation
    form_class = FormationForm
    template_name = "formations/form.html"
    success_url = reverse_lazy("formations:index")
    success_message = "La formation a été créée avec succès."
    modal_title = "Nouvelle formation"
    modal_eyebrow = "Catalogue"
    submit_label = "Enregistrer la formation"
    full_width_fields = "description objectifs programme image"


class CategorieListView(LoginRequiredMixin, ListView):
    model = CategorieFormation
    template_name = "formations/categorie_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return CategorieFormation.objects.order_by("nom")


class CategorieCreateView(HtmxModalFormMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = CategorieFormation
    form_class = CategorieFormationForm
    template_name = "formations/categorie_form.html"
    success_url = reverse_lazy("formations:categorie-list")
    success_message = "La catégorie a été enregistrée avec succès."
    modal_title = "Nouvelle catégorie"
    modal_eyebrow = "Catalogue"
    submit_label = "Enregistrer la catégorie"
    full_width_fields = "description"


class SessionListView(LoginRequiredMixin, ListView):
    model = SessionFormation
    template_name = "formations/session_list.html"
    context_object_name = "sessions"
    paginate_by = 20

    def get_queryset(self):
        return SessionFormation.objects.select_related(
            "formation", "formateur"
        ).order_by("-date_debut", "-created_at")


class SessionCreateView(HtmxModalFormMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = SessionFormation
    form_class = SessionFormationForm
    template_name = "formations/session_form.html"
    success_url = reverse_lazy("formations:session-list")
    success_message = "La session a été créée avec succès."
    modal_title = "Nouvelle session"
    modal_eyebrow = "Planification"
    submit_label = "Enregistrer la session"
    full_width_fields = "notes paiement_requis_attestation"


class SessionDetailView(LoginRequiredMixin, DetailView):
    model = SessionFormation
    template_name = "formations/session_detail.html"
    context_object_name = "session"

    def get_queryset(self):
        return SessionFormation.objects.select_related(
            "formation", "formateur"
        ).prefetch_related(
            "inscriptions__participant"
        )


class SeanceListView(LoginRequiredMixin, ListView):
    model = Seance
    template_name = "formations/seance_list.html"
    context_object_name = "seances"
    paginate_by = 20

    def get_queryset(self):
        return Seance.objects.select_related(
            "session", "session__formation"
        ).order_by("-date", "-heure_debut")


class SeanceCreateView(HtmxModalFormMixin, LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Seance
    form_class = SeanceForm
    template_name = "formations/seance_form.html"
    success_url = reverse_lazy("formations:seance-list")
    success_message = "La séance a été créée avec succès."
    modal_title = "Nouvelle séance"
    modal_eyebrow = "Planification"
    submit_label = "Enregistrer la séance"
    full_width_fields = "contenu observations"
